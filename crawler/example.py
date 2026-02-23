#!/usr/bin/env python3
# coding=utf-8
"""
NewsRadar 使用示例

演示如何在代码中使用 NewsRadarCrawler
"""

from crawler import NewsRadarCrawler


def example_basic():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 抓取所有平台")
    print("=" * 60)
    
    crawler = NewsRadarCrawler()
    results = crawler.crawl()
    
    # 打印结果
    crawler.print_results(results, limit=5)
    
    # 保存结果
    import json
    with open('example_all.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n结果已保存到 example_all.json")


def example_single_platform():
    """单个平台示例"""
    print("\n" + "=" * 60)
    print("示例2: 只抓取知乎")
    print("=" * 60)
    
    crawler = NewsRadarCrawler()
    results = crawler.crawl(platform_ids=['zhihu'])
    
    crawler.print_results(results, limit=10)


def example_multiple_platforms():
    """多个平台示例"""
    print("\n" + "=" * 60)
    print("示例3: 抓取知乎和微博")
    print("=" * 60)
    
    crawler = NewsRadarCrawler()
    results = crawler.crawl(platform_ids=['zhihu', 'weibo'])
    
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


if __name__ == "__main__":
    # 运行示例
    # example_basic()
    example_single_platform()
    # example_multiple_platforms()
    # example_with_proxy()
