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


def _ensure_webhook() -> None:
    """
    简单校验 webhook 是否已配置，未配置时直接抛出异常。
    """
    if not FEISHU_WEBHOOK_URL or "REPLACE_WITH_YOUR_WEBHOOK" in FEISHU_WEBHOOK_URL:
        raise RuntimeError(
            "飞书 Webhook 未配置，请在 NewsRadar/feishu_notifier.py 中设置 FEISHU_WEBHOOK_URL 常量。"
        )


def send_feishu_text(message: str) -> bool:
    """
    发送纯文本消息到飞书。

    Args:
        message: 要发送的文本内容

    Returns:
        bool: 发送是否成功
    """
    _ensure_webhook()

    headers = {"Content-Type": "application/json"}
    payload = {
        "msg_type": "text",
        "content": {
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


def format_crawl_results_for_feishu(
        results: Dict[str, Any],
        limit_per_platform: int = 5,
        title: Optional[str] = None,
) -> str:
    """
    将抓取结果格式化为飞书文本消息。

    设计目标：字段和最终结构参考 core/html_generator.py
    - 顶部可选标题 + 简短抓取概览
    - 下方按“类别”分组，这里类别 = 平台（platform_name）
    - 每条新闻展示为：标题 + 平台小标签 + 链接（如有，mobile_url 优先，其次 url）
    """
    lines = []

    if title:
        lines.append(title)
        lines.append("")

    summary = results.get("summary", {})
    success = summary.get("success_count", 0)
    total = summary.get("total_platforms", 0)
    failed = summary.get("failed_count", 0)

    # 简要抓取概览
    lines.append(f"本次抓取平台：{success}/{total} 成功，{failed} 失败")

    failed_platforms = summary.get("failed_platforms") or []
    if failed_platforms:
        failed_names = ", ".join(p.get("name") or p.get("id") or "" for p in failed_platforms)
        lines.append(f"失败平台：{failed_names}")

    lines.append("")

    # 按“分类”分组，参考 html_generator 的 category 概念，这里用平台名作为分组标题
    platforms = results.get("platforms") or {}
    for platform_id, data in platforms.items():
        platform_name = data.get("platform_name", platform_id)
        items = data.get("items") or []

        # 分组名称（类似 HTML 里的分类名称）
        lines.append(f"{platform_name}")

        # 每个平台最多展示 limit_per_platform 条
        for item in items[:limit_per_platform]:
            rank = item.get("rank")
            title_text = item.get("title", "")
            # 与 html_generator 一致：mobile_url 为空时用 url 兜底
            url = item.get("mobile_url") or item.get("url") or ""

            label = f"【{platform_name}】"

            prefix = f"{rank}." if rank is not None else "-"
            if url:
                # 标题 + 平台小标签 + 链接
                lines.append(f"  {prefix} {title_text} {label} {url}")
            else:
                # 无链接时仍保留平台小标签
                lines.append(f"  {prefix} {title_text} {label}")

        lines.append("")  # 平台之间空一行

    return "\n".join(lines).rstrip()


def format_news_for_feishu(
        categories: Sequence[NewsCategory],
        title: Optional[str] = None,
) -> str:
    """
    将已按类别聚合好的新闻（list[NewsCategory]）格式化为飞书文本消息。

    最终结构参考 core/html_generator.generate_html：
    - 每个分类一块：使用 category 字段作为分组名称
    - 每条新闻：标题 + 若干平台小标签，如【参考消息】
      - 小标签部分为超链接，点击跳转到对应 URL（mobile_url 优先，其次 url）
    """
    lines: list[str] = []

    if title:
        lines.append(title)
        lines.append("")

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


def send_crawl_results_to_feishu(
        results: Dict[str, Any],
        limit_per_platform: int = 5,
        title: Optional[str] = None,
) -> bool:
    """
    直接将 NewsRadar 抓取结果格式化后发送到飞书。

    Args:
        results: NewsRadarCrawler.crawl() 返回的结果字典
        limit_per_platform: 每个平台最多展示的条目数
        title: 顶部标题（可选）

    Returns:
        bool: 发送是否成功
    """
    text = format_crawl_results_for_feishu(
        results=results,
        limit_per_platform=limit_per_platform,
        title=title,
    )
    return send_feishu_text(text)


def send_news_results_to_feishu(
        categories: Sequence[NewsCategory],
) -> bool:
    text = format_news_for_feishu(categories)
    return send_feishu_text(text)


__all__ = [
    "FEISHU_WEBHOOK_URL",
    "send_feishu_text",
    "format_crawl_results_for_feishu",
    "format_news_for_feishu",
    "send_crawl_results_to_feishu",
]
