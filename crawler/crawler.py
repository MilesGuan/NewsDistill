#!/usr/bin/env python3
# coding=utf-8
"""
NewsRadar - 热榜数据抓取工具

独立运行的热榜数据抓取脚本，使用 NewsNow API 获取多平台热榜数据。
支持的平台硬编码在代码中，无需配置文件。

使用方法:
    python crawler.py                    # 抓取所有平台
    python crawler.py --platform zhihu   # 只抓取知乎
    python crawler.py --platform zhihu weibo  # 抓取指定平台
    python crawler.py --output results.json   # 保存结果到文件
"""

import json
import random
import time
import argparse
import concurrent.futures
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime

import requests


class NewsRadarCrawler:
    """热榜数据抓取器"""

    # NewsNow API 地址
    API_URL = "https://newsnow.busiyi.world/api/s"

    # 支持的平台列表（硬编码）
    SUPPORTED_PLATFORMS = {
        # === 综合新闻媒体类 ===
        "toutiao": "今日头条",
        "baidu": "百度热搜",
        "thepaper": "澎湃新闻",
        "ifeng": "凤凰网",
        "cankaoxiaoxi": "参考消息",
        "sputniknewscn": "卫星通讯社",
        "zaobao": "联合早报",
        "mktnews": "MKT新闻",
        "kaopu": "靠谱新闻",
        "tencent-hot": "腾讯新闻 综合早报",
        
        # === 财经投资类 ===
        "wallstreetcn-hot": "华尔街见闻 最热",
        "wallstreetcn-quick": "华尔街见闻 快讯",
        "wallstreetcn-news": "华尔街见闻 最新",
        "cls-hot": "财联社热门",
        "cls-telegraph": "财联社 电报",
        "cls-depth": "财联社 深度",
        "gelonghui": "格隆汇",
        "jin10": "金十数据",
        "fastbull": "快讯通",
        "fastbull-express": "法布财经 快讯",
        "fastbull-news": "法布财经 头条",
        
        # === 社交/短视频/娱乐类 ===
        "weibo": "微博",
        "douyin": "抖音",
        "bilibili-hot-search": "bilibili 热搜",
        "tieba": "贴吧",
        "zhihu": "知乎",
        "hupu": "虎扑",
        
        # === 科技类平台 ===
        "ithome": "IT之家",
        "juejin": "掘金",
        "hackernews": "Hacker News",
        "solidot": "Solidot",
        "v2ex": "V2EX",
        "sspai": "少数派",
        "producthunt": "ProductHunt",
    }

    # 默认请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        """
        初始化抓取器

        Args:
            proxy_url: 代理服务器 URL（可选）
            api_url: API 基础 URL（可选，默认使用 API_URL）
        """
        self.proxy_url = proxy_url
        self.api_url = api_url or self.API_URL

    def fetch_platform(
        self,
        platform_id: str,
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5,
    ) -> Tuple[Optional[Dict], str, str]:
        """
        获取指定平台的热榜数据，支持重试

        Args:
            platform_id: 平台ID
            max_retries: 最大重试次数
            min_retry_wait: 最小重试等待时间（秒）
            max_retry_wait: 最大重试等待时间（秒）

        Returns:
            (数据字典, 平台ID, 平台名称) 元组，失败时数据字典为 None
        """
        platform_name = self.SUPPORTED_PLATFORMS.get(platform_id, platform_id)
        url = f"{self.api_url}?id={platform_id}&latest"

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    url,
                    proxies=proxies,
                    headers=self.DEFAULT_HEADERS,
                    timeout=10,
                )
                response.raise_for_status()

                data_json = response.json()
                status = data_json.get("status", "未知")
                
                if status not in ["success", "cache"]:
                    raise ValueError(f"响应状态异常: {status}")

                status_info = "最新数据" if status == "success" else "缓存数据"
                print(f"✓ 获取 {platform_name} ({platform_id}) 成功（{status_info}）")
                
                # 解析数据
                items = data_json.get("items", [])
                parsed_data = {
                    "platform_id": platform_id,
                    "platform_name": platform_name,
                    "status": status,
                    "timestamp": datetime.now().isoformat(),
                    "items": []
                }

                for index, item in enumerate(items, 1):
                    title = item.get("title")
                    # 跳过无效标题
                    if title is None or isinstance(title, float) or not str(title).strip():
                        continue
                    
                    parsed_data["items"].append({
                        "rank": index,
                        "title": str(title).strip(),
                        "url": item.get("url", ""),
                        "mobile_url": item.get("mobileUrl", ""),
                    })

                return parsed_data, platform_id, platform_name

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(min_retry_wait, max_retry_wait)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    print(f"✗ 请求 {platform_name} ({platform_id}) 失败: {e}. {wait_time:.2f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"✗ 请求 {platform_name} ({platform_id}) 失败: {e}")
                    return None, platform_id, platform_name

        return None, platform_id, platform_name

    def crawl(
        self,
        platform_ids: Optional[List[str]] = None,
        request_interval: int = 100,
        max_workers: int = 8,
    ) -> Dict:
        """
        爬取多个平台的热榜数据

        Args:
            platform_ids: 平台ID列表，None 表示抓取所有支持的平台
            request_interval: 请求间隔（毫秒）
            max_workers: 并行抓取的最大线程数（默认8）

        Returns:
            包含所有平台数据的字典
        """
        # 确定要抓取的平台列表
        if platform_ids is None:
            target_platforms = list(self.SUPPORTED_PLATFORMS.keys())
        else:
            # 验证平台ID是否支持
            invalid_platforms = [pid for pid in platform_ids if pid not in self.SUPPORTED_PLATFORMS]
            if invalid_platforms:
                raise ValueError(
                    f"不支持的平台ID: {invalid_platforms}\n"
                    f"支持的平台: {list(self.SUPPORTED_PLATFORMS.keys())}"
                )
            target_platforms = platform_ids

        print(f"\n开始抓取 {len(target_platforms)} 个平台的热榜数据...")
        print(f"平台列表: {', '.join([self.SUPPORTED_PLATFORMS[pid] for pid in target_platforms])}\n")

        results = {
            "crawl_time": datetime.now().isoformat(),
            "platforms": {},
            "summary": {
                "total_platforms": len(target_platforms),
                "success_count": 0,
                "failed_count": 0,
                "failed_platforms": []
            }
        }

        # 并行抓取平台数据（I/O 密集型：用线程池即可）
        # 为了尽量保留原先的“间隔请求”节奏，这里对每个任务做按序延迟启动（stagger）。
        def _fetch_with_stagger(idx: int, pid: str):
            if request_interval > 0 and idx > 0:
                # 轻微抖动，避免固定节奏被限流；保持下限 0ms
                jitter_ms = random.randint(-10, 20)
                delay_ms = max(0, idx * request_interval + jitter_ms)
                time.sleep(delay_ms / 1000)
            return self.fetch_platform(pid)

        workers = max(1, min(int(max_workers), len(target_platforms)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_fetch_with_stagger, i, platform_id): platform_id
                for i, platform_id in enumerate(target_platforms)
            }

            for future in concurrent.futures.as_completed(futures):
                data, pid, pname = future.result()
                if data:
                    results["platforms"][pid] = data
                    results["summary"]["success_count"] += 1
                else:
                    results["summary"]["failed_count"] += 1
                    results["summary"]["failed_platforms"].append({"id": pid, "name": pname})

        # 打印摘要
        print(f"\n{'='*60}")
        print(f"抓取完成！")
        print(f"成功: {results['summary']['success_count']}/{results['summary']['total_platforms']}")
        if results['summary']['failed_count'] > 0:
            failed_names = [p['name'] for p in results['summary']['failed_platforms']]
            print(f"失败: {', '.join(failed_names)}")
        print(f"{'='*60}\n")

        return results

    def print_results(self, results: Dict, limit: int = 10):
        """
        打印抓取结果

        Args:
            results: 抓取结果字典
            limit: 每个平台最多显示的热榜条目数
        """
        for platform_id, platform_data in results["platforms"].items():
            platform_name = platform_data["platform_name"]
            items = platform_data["items"]
            
            print(f"\n【{platform_name}】")
            print(f"共 {len(items)} 条热榜")
            
            for item in items[:limit]:
                print(f"  {item['rank']:2d}. {item['title']}")
                if item.get('url'):
                    print(f"      {item['url']}")
            
            if len(items) > limit:
                print(f"  ... 还有 {len(items) - limit} 条")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="NewsRadar - 热榜数据抓取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python crawler.py                           # 抓取所有平台
  python crawler.py --platform zhihu          # 只抓取知乎
  python crawler.py --platform zhihu weibo    # 抓取知乎和微博
  python crawler.py --output results.json     # 保存结果到文件
  python crawler.py --platform zhihu --output zhihu.json --limit 20
        """
    )
    
    parser.add_argument(
        "--platform",
        nargs="+",
        help="指定要抓取的平台ID（可多个），不指定则抓取所有平台"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="将结果保存到JSON文件"
    )
    
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="打印时每个平台最多显示的热榜条目数（默认10）"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=100,
        help="请求间隔（毫秒，默认100）"
    )
    
    parser.add_argument(
        "--proxy",
        help="代理服务器URL（如: http://127.0.0.1:7890）"
    )
    
    parser.add_argument(
        "--list-platforms",
        action="store_true",
        help="列出所有支持的平台"
    )

    args = parser.parse_args()

    # 列出支持的平台
    if args.list_platforms:
        print("支持的平台列表:")
        for pid, pname in NewsRadarCrawler.SUPPORTED_PLATFORMS.items():
            print(f"  {pid:20s} - {pname}")
        return

    # 创建抓取器
    crawler = NewsRadarCrawler(proxy_url=args.proxy)

    # 执行抓取
    try:
        results = crawler.crawl(
            platform_ids=args.platform,
            request_interval=args.interval
        )
    except ValueError as e:
        print(f"错误: {e}")
        return

    # 打印结果
    crawler.print_results(results, limit=args.limit)

    # 保存到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
