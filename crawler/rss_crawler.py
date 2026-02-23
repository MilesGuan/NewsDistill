#!/usr/bin/env python3
# coding=utf-8
"""
NewsRadar - RSS 抓取工具

独立运行的 RSS 抓取脚本，不依赖 YAML 配置。
支持的 RSS 源在代码中硬编码，开箱即用。

示例用法:
    python rss_crawler.py                      # 抓取所有内置 RSS 源
    python rss_crawler.py --feed hacker-news   # 只抓取指定源
    python rss_crawler.py --feed hacker-news sspai --days 7
    python rss_crawler.py --output rss.json    # 保存结果到文件
"""

import argparse
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import feedparser
import requests


@dataclass
class RSSFeed:
    """RSS 源配置（硬编码）"""

    id: str
    name: str
    url: str
    max_items: int = 0  # 0 = 不限制


@dataclass
class RSSArticle:
    """标准化后的 RSS 文章结构"""

    feed_id: str
    feed_name: str
    title: str
    url: str
    published_at: Optional[str]
    summary: str
    author: str


class RSSCrawler:
    """RSS 抓取器（独立版）"""

    # 内置支持的 RSS 源（可按需增减）
    SUPPORTED_FEEDS: Dict[str, RSSFeed] = {
        "hacker-news": RSSFeed(
            id="hacker-news",
            name="Hacker News",
            url="https://news.ycombinator.com/rss",
        ),
        "sspai": RSSFeed(
            id="sspai",
            name="少数派",
            url="https://sspai.com/feed",
        ),
        "36kr": RSSFeed(
            id="36kr",
            name="36氪",
            url="https://36kr.com/feed",
        ),
        "solidot": RSSFeed(
            id="solidot",
            name="Solidot",
            url="https://www.solidot.org/index.rss",
        ),
        "ithome": RSSFeed(
            id="ithome",
            name="IT之家",
            url="https://www.ithome.com/rss/",
        ),
        "ph": RSSFeed(
            id="ph",
            name="Product Hunt",
            url="https://www.producthunt.com/feed",
        ),
    }

    DEFAULT_HEADERS = {
        "User-Agent": "NewsRadar-RSS/1.0 (+https://github.com/trendradar)",
        "Accept": "application/feed+json, application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        timeout: int = 15,
    ):
        """
        初始化抓取器

        Args:
            proxy_url: 代理服务器 URL（可选）
            timeout: 请求超时（秒）
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

        if proxy_url:
            self.session.proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }

    @staticmethod
    def _normalize_datetime(entry) -> Optional[datetime]:
        """从 feedparser 条目中提取发布时间"""
        dt = None
        for attr in ("published_parsed", "updated_parsed", "created_parsed"):
            value = getattr(entry, attr, None)
            if value:
                try:
                    dt = datetime(*value[:6])
                    break
                except Exception:
                    continue
        return dt

    def fetch_feed(
        self,
        feed: RSSFeed,
        max_age_days: Optional[int] = None,
    ) -> Tuple[List[RSSArticle], Optional[str]]:
        """
        抓取单个 RSS 源

        Args:
            feed: RSS 源配置
            max_age_days: 最大保留天数（None=不过滤，0=不过滤，>0=只保留最近 N 天）

        Returns:
            (文章列表, 错误信息) 元组
        """
        try:
            resp = self.session.get(feed.url, timeout=self.timeout)
            resp.raise_for_status()

            parsed = feedparser.parse(resp.content)
            if parsed.bozo:
                # bozo 标志表示解析时有潜在问题，但一般仍能取到条目
                pass

            articles: List[RSSArticle] = []
            now = datetime.utcnow()
            cutoff: Optional[datetime] = None
            if max_age_days and max_age_days > 0:
                cutoff = now - timedelta(days=max_age_days)

            for idx, entry in enumerate(parsed.entries):
                if feed.max_items and idx >= feed.max_items:
                    break

                dt = self._normalize_datetime(entry)
                if cutoff and dt and dt < cutoff:
                    # 过旧的文章直接跳过
                    continue

                title = getattr(entry, "title", "").strip()
                if not title:
                    continue

                link = getattr(entry, "link", "").strip()
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                author = getattr(entry, "author", "") or getattr(entry, "author_detail", {}).get("name", "")

                published_str = dt.isoformat() if dt else None

                articles.append(
                    RSSArticle(
                        feed_id=feed.id,
                        feed_name=feed.name,
                        title=title,
                        url=link,
                        published_at=published_str,
                        summary=summary,
                        author=author,
                    )
                )

            print(f"[RSS] {feed.name}: 获取 {len(articles)} 条")
            return articles, None

        except requests.Timeout:
            error = f"请求超时 ({self.timeout}s)"
            print(f"[RSS] {feed.name}: {error}")
            return [], error
        except requests.RequestException as e:
            error = f"请求失败: {e}"
            print(f"[RSS] {feed.name}: {error}")
            return [], error
        except Exception as e:
            error = f"未知错误: {e}"
            print(f"[RSS] {feed.name}: {error}")
            return [], error

    def crawl(
        self,
        feed_ids: Optional[List[str]] = None,
        request_interval: int = 2000,
        max_age_days: Optional[int] = None,
    ) -> Dict:
        """
        抓取多个 RSS 源

        Args:
            feed_ids: 源 ID 列表，None 表示抓取所有内置源
            request_interval: 源之间的请求间隔（毫秒）
            max_age_days: 最大保留天数（None/0 表示不过滤）

        Returns:
            标准化后的结果字典，适合直接序列化为 JSON
        """
        # 确定要抓取的源
        if feed_ids is None:
            targets = list(self.SUPPORTED_FEEDS.values())
        else:
            invalid = [fid for fid in feed_ids if fid not in self.SUPPORTED_FEEDS]
            if invalid:
                raise ValueError(
                    f"不支持的 RSS 源 ID: {invalid}\n"
                    f"支持的源: {list(self.SUPPORTED_FEEDS.keys())}"
                )
            targets = [self.SUPPORTED_FEEDS[fid] for fid in feed_ids]

        print(f"\n开始抓取 {len(targets)} 个 RSS 源...")
        print("源列表: " + ", ".join([f.name for f in targets]) + "\n")

        now = datetime.utcnow()
        results: Dict[str, Dict] = {
            "crawl_time": now.isoformat(),
            "feeds": {},
            "summary": {
                "total_feeds": len(targets),
                "success_count": 0,
                "failed_count": 0,
                "failed_feeds": [],
                "total_articles": 0,
            },
        }

        for i, feed in enumerate(targets):
            articles, error = self.fetch_feed(feed, max_age_days=max_age_days)

            if error:
                results["summary"]["failed_count"] += 1
                results["summary"]["failed_feeds"].append(
                    {"id": feed.id, "name": feed.name, "error": error}
                )
            else:
                results["summary"]["success_count"] += 1
                results["summary"]["total_articles"] += len(articles)
                results["feeds"][feed.id] = {
                    "feed_id": feed.id,
                    "feed_name": feed.name,
                    "url": feed.url,
                    "articles": [asdict(a) for a in articles],
                }

            # 间隔请求（除最后一个）
            if i < len(targets) - 1 and request_interval > 0:
                time.sleep(request_interval / 1000.0)

        print("\n" + "=" * 60)
        print("RSS 抓取完成！")
        print(
            f"成功: {results['summary']['success_count']}/"
            f"{results['summary']['total_feeds']}, "
            f"文章总数: {results['summary']['total_articles']}"
        )
        if results["summary"]["failed_count"] > 0:
            failed_names = [f['name'] for f in results["summary"]["failed_feeds"]]
            print("失败: " + ", ".join(failed_names))
        print("=" * 60 + "\n")

        return results

    @classmethod
    def list_supported_feeds(cls) -> List[Tuple[str, str, str]]:
        """列出所有内置支持的 RSS 源"""
        return [
            (feed.id, feed.name, feed.url)
            for feed in cls.SUPPORTED_FEEDS.values()
        ]

    @staticmethod
    def print_results(results: Dict, limit: int = 5) -> None:
        """在终端友好地打印部分结果"""
        for feed_id, data in results.get("feeds", {}).items():
            name = data["feed_name"]
            articles = data["articles"]

            print(f"\n【{name}】")
            print(f"共 {len(articles)} 篇文章")

            for art in articles[:limit]:
                title = art["title"]
                url = art["url"]
                published = art.get("published_at") or ""
                print(f"  - {title}")
                if published:
                    print(f"    时间: {published}")
                if url:
                    print(f"    链接: {url}")

            if len(articles) > limit:
                print(f"  ... 还有 {len(articles) - limit} 篇")


def main() -> None:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="NewsRadar - RSS 抓取工具（独立版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python rss_crawler.py                           # 抓取所有内置 RSS 源
  python rss_crawler.py --feed hacker-news        # 只抓取 Hacker News
  python rss_crawler.py --feed hacker-news sspai  # 抓取多个源
  python rss_crawler.py --days 3                  # 只保留最近 3 天文章
  python rss_crawler.py --output rss.json         # 将结果保存到 JSON 文件
        """,
    )

    parser.add_argument(
        "--feed",
        nargs="+",
        help="指定要抓取的 RSS 源 ID（可多个），不指定则抓取所有内置源",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="只保留最近 N 天的文章（默认不过滤）",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="将结果保存为 JSON 文件",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=5,
        help="打印时每个源显示的文章数量（默认 5）",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2000,
        help="源之间的请求间隔（毫秒，默认 2000）",
    )
    parser.add_argument(
        "--proxy",
        help="HTTP 代理地址（如 http://127.0.0.1:7890）",
    )
    parser.add_argument(
        "--list-feeds",
        action="store_true",
        help="列出所有内置支持的 RSS 源",
    )

    args = parser.parse_args()

    if args.list_feeds:
        print("内置支持的 RSS 源:")
        for fid, name, url in RSSCrawler.list_supported_feeds():
            print(f"  {fid:15s} - {name:10s} - {url}")
        return

    crawler = RSSCrawler(proxy_url=args.proxy)

    try:
        results = crawler.crawl(
            feed_ids=args.feed,
            request_interval=args.interval,
            max_age_days=args.days,
        )
    except ValueError as e:
        print(f"错误: {e}")
        return

    RSSCrawler.print_results(results, limit=args.limit)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")


if __name__ == "__main__":
    main()

