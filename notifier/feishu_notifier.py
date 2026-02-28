#!/usr/bin/env python3
# coding=utf-8
"""
飞书通知模块

"""

import json
from typing import Dict, Any, Optional, Sequence

import requests

import envUtils
from db.models import NewsCategory, MergedNewsItem, NewsItem

# === 在这里写死飞书 Webhook 等配置 ===
# 请将下面的占位符替换为你自己的飞书机器人 Webhook 地址
FEISHU_WEBHOOK_URL: str = envUtils.webhook_feishu

# 发送超时时间（秒）
REQUEST_TIMEOUT: int = 30


def _ensure_webhook():
    """
    简单校验 webhook 是否已配置，未配置时直接抛出异常。
    """
    if not FEISHU_WEBHOOK_URL or "REPLACE_WITH_YOUR_WEBHOOK" in FEISHU_WEBHOOK_URL:
        raise RuntimeError(
            "飞书 Webhook 未配置，请在 NewsRadar/feishu_notifier.py 中设置 FEISHU_WEBHOOK_URL 常量。"
        )


def send_feishu_text(title: str, message: str) -> bool:
    """
    发送纯文本消息到飞书。

    Args:
        title: 消息标题
        message: 要发送的文本内容

    Returns:
        bool: 发送是否成功
    """
    _ensure_webhook()

    headers = {"Content-Type": "application/json"}
    payload = {
        "message_type": "text",
        "content": {
            "title": title,
            "text": message,
        },
    }

    try:
        resp = requests.post(
            FEISHU_WEBHOOK_URL,
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            print(f"[Feishu] 请求失败，HTTP {resp.status_code}: {resp.text}")
            return False

        data = {}
        try:
            data = resp.json()
        except Exception:
            # 部分实现可能返回空响应，这里做兼容
            pass

        # 飞书自建应用机器人通常使用 code 字段，自定义机器人使用 StatusCode
        code = data.get("code", data.get("StatusCode", 0))
        if code == 0:
            print("[Feishu] 文本消息发送成功")
            return True

        print(f"[Feishu] 文本消息发送失败，返回: {data}")
        return False
    except Exception as e:
        print(f"[Feishu] 文本消息发送异常: {e}")
        return False


def format_news_for_feishu(
        categories: Sequence[NewsCategory],
) -> str:
    """
    将已按类别聚合好的新闻（list[NewsCategory]）格式化为飞书文本消息。

    最终结构参考 core/html_generator.generate_html：
    - 每个分类一块：使用 category 字段作为分组名称
    - 每条新闻：标题 + 若干平台小标签，如【参考消息】
      - 小标签部分为超链接，点击跳转到对应 URL（mobile_url 优先，其次 url）
    """
    lines: list[str] = []
    for category in categories:
        if not category.items:
            continue

        # 分类名称（加粗）
        cat_name = category.category or ""
        if not cat_name:
            continue
        lines.append(f"**{cat_name}**")

        # 分类下每条聚合新闻
        for merged in category.items:
            base = merged.title or ""
            if not base:
                continue

            # 平台小标签部分：按 HTML 逻辑，遍历 merged.news
            source_tokens: list[str] = []
            for n in merged.news:
                platform_name = n.platform_name or n.platform_id or ""
                if not platform_name:
                    continue
                label = f"【{platform_name}】"
                # 优先使用移动端链接，缺省时回退到普通 URL
                url = n.mobile_url or n.url or ""
                if url:
                    # 飞书 text 消息支持 markdown 链接语法
                    source_tokens.append(f"[{label}]({url})")
                else:
                    source_tokens.append(label)

            if source_tokens:
                # 标题后留一个空格，多个平台标签之间不再额外加空格，视觉上更紧凑
                line = f"{base} " + "".join(source_tokens)
            else:
                line = base

            lines.append(f"  - {line}")

        # 分类之间空一行
        lines.append("")

    return "\n".join(lines).rstrip()


def send_news_results_to_feishu(
        title,
        categories: Sequence[NewsCategory],
) -> bool:
    text = format_news_for_feishu(categories)
    return send_feishu_text(title, text)


__all__ = [
    "FEISHU_WEBHOOK_URL",
    "send_feishu_text",
    "format_news_for_feishu",
]
