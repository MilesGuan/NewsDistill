#!/usr/bin/env python3
# coding=utf-8
"""
数据库使用示例

演示如何使用 NewsDatabase 进行数据读写操作
"""

from datetime import datetime
from .database import NewsDatabase
from .models import NewsData, NewsItem


def example_save_data():
    """示例：保存抓取的数据到数据库"""
    print("=" * 60)
    print("示例1: 保存数据到数据库")
    print("=" * 60)

    # 创建数据库实例
    db = NewsDatabase(db_path="example.db")

    # 模拟抓取到的数据
    news_data = NewsData(
        date="2026-02-20",
        crawl_time="14:30",
        items={
            "zhihu": [
                NewsItem(
                    title="AI 技术的最新进展",
                    platform_id="zhihu",
                    platform_name="知乎",
                    rank=1,
                    url="https://www.zhihu.com/question/123456",
                    mobile_url="https://www.zhihu.com/question/123456",
                    crawl_time="14:30"
                ),
                NewsItem(
                    title="Python 编程技巧分享",
                    platform_id="zhihu",
                    platform_name="知乎",
                    rank=2,
                    url="https://www.zhihu.com/question/789012",
                    mobile_url="https://www.zhihu.com/question/789012",
                    crawl_time="14:30"
                ),
            ],
            "weibo": [
                NewsItem(
                    title="今日热点话题",
                    platform_id="weibo",
                    platform_name="微博",
                    rank=1,
                    url="https://s.weibo.com/weibo?q=热点&band_rank=1",
                    mobile_url="https://m.weibo.com/search?q=热点",
                    crawl_time="14:30"
                ),
            ],
        },
        id_to_name={
            "zhihu": "知乎",
            "weibo": "微博",
        },
        failed_ids=[]
    )

    # 保存到数据库
    success, new_count, updated_count = db.save_news_data(news_data)
    print(f"保存结果: success={success}, 新增={new_count}, 更新={updated_count}")


def example_query_data():
    """示例：查询数据库中的数据"""
    print("\n" + "=" * 60)
    print("示例2: 查询数据")
    print("=" * 60)

    db = NewsDatabase(db_path="example.db")

    # 查询今天的新闻
    print("\n--- 查询今天的新闻 ---")
    today_news = db.get_latest_news(limit=10)
    print(f"找到 {len(today_news)} 条新闻")
    for item in today_news[:5]:
        print(f"  [{item['platform_id']}] {item['title'][:50]}... (排名: {item['rank']})")

    # 查询指定平台的新闻
    print("\n--- 查询知乎的新闻 ---")
    zhihu_news = db.get_news_by_platform("zhihu", limit=5)
    print(f"找到 {len(zhihu_news)} 条知乎新闻")
    for item in zhihu_news:
        print(f"  {item['title'][:50]}... (排名: {item['rank']})")

    # 搜索新闻
    print("\n--- 搜索包含 'AI' 的新闻 ---")
    ai_news = db.search_news("AI", limit=5)
    print(f"找到 {len(ai_news)} 条相关新闻")
    for item in ai_news:
        print(f"  [{item['platform_id']}] {item['title'][:50]}...")


def example_statistics():
    """示例：获取统计信息"""
    print("\n" + "=" * 60)
    print("示例3: 数据库统计信息")
    print("=" * 60)

    db = NewsDatabase(db_path="example.db")
    stats = db.get_statistics()

    print(f"\n总记录数: {stats['total_items']}")
    print(f"最新抓取时间: {stats['latest_crawl_time']}")
    print("\n按平台统计:")
    for platform_id, count in stats['by_platform'].items():
        print(f"  {platform_id}: {count} 条")


def example_integration_with_crawler():
    """示例：与爬虫集成"""
    print("\n" + "=" * 60)
    print("示例4: 与爬虫集成")
    print("=" * 60)

    # 假设这是从 crawler.py 获取的数据格式
    crawl_results = {
        "platforms": {
            "zhihu": {
                "platform_id": "zhihu",
                "platform_name": "知乎",
                "items": [
                    {"rank": 1, "title": "测试新闻1", "url": "https://example.com/1"},
                    {"rank": 2, "title": "测试新闻2", "url": "https://example.com/2"},
                ]
            }
        },
        "summary": {
            "failed_platforms": []
        }
    }

    # 转换为 NewsData 格式
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    items = {}
    id_to_name = {}
    failed_ids = []

    for platform_id, platform_data in crawl_results["platforms"].items():
        platform_name = platform_data["platform_name"]
        id_to_name[platform_id] = platform_name

        news_list = []
        for item_data in platform_data["items"]:
            news_item = NewsItem(
                title=item_data["title"],
                platform_id=platform_id,
                platform_name=platform_name,
                rank=item_data["rank"],
                url=item_data.get("url", ""),
                mobile_url=item_data.get("mobile_url", ""),
                crawl_time=now_time
            )
            news_list.append(news_item)

        items[platform_id] = news_list

    news_data = NewsData(
        date=today,
        crawl_time=now_time,
        items=items,
        id_to_name=id_to_name,
        failed_ids=failed_ids
    )

    # 保存到数据库
    db = NewsDatabase(db_path="example.db")
    success, new_count, updated_count = db.save_news_data(news_data)
    print(f"保存完成: 新增={new_count}, 更新={updated_count}")


if __name__ == "__main__":
    # 运行示例
    example_save_data()
    example_query_data()
    example_statistics()
    example_integration_with_crawler()
