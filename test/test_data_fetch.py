#!/usr/bin/env python3
# coding=utf-8
"""
基于 NewsRadarCrawler 的数据抓取示例

迁移自 crawler/example.py，方便在 test 环境下手动运行。
"""
from core.data_fetch import fetch_news
from crawler import NewsRadarCrawler


def example_single_platform():
    """单个平台示例"""
    print("\n" + "=" * 60)
    print("示例2: 只抓取知乎")
    print("=" * 60)

    crawler = NewsRadarCrawler()
    results = crawler.crawl(platform_ids=["zhihu"])

    crawler.print_results(results, limit=10)


def example_multiple_platforms():
    """多个平台示例"""
    print("\n" + "=" * 60)
    print("示例3: 抓取知乎和微博")
    print("=" * 60)

    crawler = NewsRadarCrawler()
    results = crawler.crawl(platform_ids=["zhihu", "weibo"])

    crawler.print_results(results, limit=10)


def example_with_proxy():
    """使用代理示例"""
    print("\n" + "=" * 60)
    print("示例4: 使用代理抓取")
    print("=" * 60)

    # 注意：这里只是示例，实际使用时需要配置有效的代理地址
    # crawler = NewsRadarCrawler(proxy_url="http://127.0.0.1:7890")
    # results = crawler.crawl(platform_ids=['zhihu'])
    # crawler.print_results(results)

    print("（示例代码已注释，需要代理时取消注释并配置代理地址）")


def test_increment_news():
    platform_ids = ["thepaper", "cankaoxiaoxi"]
    increment_news = fetch_news(platform_ids, only_increment=True)
    print(increment_news)
