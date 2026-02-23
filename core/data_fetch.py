# coding=utf-8
"""
新闻抓取任务模块

提供新闻抓取、数据库存储和增量数据识别功能
"""

from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from crawler.crawler import NewsRadarCrawler
from db.database import NewsDatabase
from db.models import NewsData, NewsItem
from db.utils import normalize_url

# 项目根目录（core 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# 1 抓取指定平台新闻(参数传入)，记录完整数据。
# 2 写入或者更新到数据库，数据库名为当天日期 如2026-02-11.db。记录数据库中不存在的增量数据
# 3 返回完整数据和增量数据
def fetch_news(platform_ids: List[str], db_dir: Optional[str] = None) -> Tuple[Optional[NewsData], Optional[NewsData]]:
    """
    抓取指定平台的新闻数据，保存到数据库，并返回完整数据和增量数据
    
    Args:
        platform_ids: 平台ID列表，如 ["zhihu", "toutiao"]
        db_dir: 数据库文件存储目录，默认为项目根目录下的 output/db
    
    Returns:
        (full_news, increment_news) 元组
        - full_news: 本次抓取的所有新闻数据
        - increment_news: 数据库中不存在的增量数据（仅新增的新闻）
    """
    # 获取当前日期，用于数据库文件名
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")
    
    # 数据库路径：默认为项目根目录下的 output/db
    if db_dir is None:
        db_dir = str(PROJECT_ROOT / "output" / "db")
    db_dir_path = Path(db_dir)
    db_path = db_dir_path / f"{today}.db"

    # 确保目录存在且为目录（若 output/db 误建为文件则删除）
    if db_dir_path.exists() and db_dir_path.is_file():
        db_dir_path.unlink()
    db_dir_path.mkdir(parents=True, exist_ok=True)

    # 若 db 文件已存在但非有效 SQLite 格式，删除后由 NewsDatabase 重建
    if db_path.exists():
        try:
            with open(db_path, "rb") as f:
                header = f.read(16)
            if not header.startswith(b"SQLite format 3\x00"):
                db_path.unlink()
        except Exception:
            db_path.unlink()
    
    # 初始化爬虫
    crawler = NewsRadarCrawler()
    
    # 抓取新闻数据
    print(f"\n开始抓取平台: {', '.join(platform_ids)}")
    crawl_results = crawler.crawl(platform_ids=platform_ids)
    
    # 转换为 NewsData 格式
    items: Dict[str, List[NewsItem]] = {}
    id_to_name: Dict[str, str] = {}
    failed_ids: List[str] = []
    
    for platform_id, platform_data in crawl_results.get("platforms", {}).items():
        platform_name = platform_data.get("platform_name", platform_id)
        id_to_name[platform_id] = platform_name
        
        news_list = []
        for item_data in platform_data.get("items", []):
            news_item = NewsItem(
                title=item_data.get("title", ""),
                platform_id=platform_id,
                platform_name=platform_name,
                rank=item_data.get("rank", 0),
                url=item_data.get("url", ""),
                mobile_url=item_data.get("mobile_url", ""),
                crawl_time=now_time
            )
            news_list.append(news_item)
        
        items[platform_id] = news_list
    
    # 记录失败的平台
    for failed_platform in crawl_results.get("summary", {}).get("failed_platforms", []):
        failed_ids.append(failed_platform.get("id", ""))
    
    # 创建完整新闻数据对象
    full_news = NewsData(
        date=today,
        crawl_time=now_time,
        items=items,
        id_to_name=id_to_name,
        failed_ids=failed_ids
    )
    
    # 查询数据库中已存在的URL，用于识别增量数据
    db = NewsDatabase(db_path=str(db_path))
    
    # 获取数据库中已存在的URL集合（用于判断增量）
    existing_urls: Dict[str, set] = {}  # {platform_id: {normalized_urls}}
    
    for platform_id in platform_ids:
        existing_urls[platform_id] = set()
        # 查询该平台的所有新闻
        existing_news = db.get_news_by_platform(platform_id)
        for news in existing_news:
            url = news.get("url", "")
            if url:
                normalized = normalize_url(url, platform_id)
                existing_urls[platform_id].add(normalized)
    
    # 识别增量数据（数据库中不存在的新闻）
    increment_items: Dict[str, List[NewsItem]] = {}
    
    for platform_id, news_list in items.items():
        increment_list = []
        for news_item in news_list:
            normalized_url = normalize_url(news_item.url, platform_id) if news_item.url else ""
            
            # 如果URL为空，或者URL不在已存在集合中，则认为是增量数据
            if not normalized_url or normalized_url not in existing_urls.get(platform_id, set()):
                increment_list.append(news_item)
        
        if increment_list:
            increment_items[platform_id] = increment_list
    
    # 创建增量新闻数据对象
    increment_news = NewsData(
        date=today,
        crawl_time=now_time,
        items=increment_items,
        id_to_name=id_to_name,
        failed_ids=failed_ids
    ) if increment_items else None
    
    # 保存完整数据到数据库
    success, new_count, updated_count = db.save_news_data(full_news)
    
    if success:
        print(f"\n数据库保存成功: 新增 {new_count} 条，更新 {updated_count} 条")
        print(f"数据库文件: {db_path}")
    else:
        print(f"\n数据库保存失败")
    
    return full_news, increment_news


def main():
    """测试用的main函数，使用知乎和今日头条作为入参测试"""
    print("=" * 60)
    print("新闻抓取测试")
    print("=" * 60)
    
    # 使用知乎和今日头条进行测试
    platform_ids = ["zhihu", "toutiao"]
    
    # 执行抓取
    full_news, increment_news = fetch_news(platform_ids)
    
    # 打印结果
    print("\n" + "=" * 60)
    print("抓取结果汇总")
    print("=" * 60)
    
    if full_news:
        print(f"\n【完整数据】")
        print(f"日期: {full_news.date}")
        print(f"抓取时间: {full_news.crawl_time}")
        print(f"平台数量: {len(full_news.items)}")
        
        total_items = sum(len(news_list) for news_list in full_news.items.values())
        print(f"新闻总数: {total_items}")
        
        for platform_id, news_list in full_news.items.items():
            platform_name = full_news.id_to_name.get(platform_id, platform_id)
            print(f"\n  {platform_name} ({platform_id}): {len(news_list)} 条")
            for item in news_list[:5]:  # 只显示前5条
                print(f"    {item.rank}. {item.title[:50]}...")
            if len(news_list) > 5:
                print(f"    ... 还有 {len(news_list) - 5} 条")
    
    if increment_news:
        print(f"\n【增量数据】")
        total_increment = sum(len(news_list) for news_list in increment_news.items.values())
        print(f"新增新闻数: {total_increment}")
        
        for platform_id, news_list in increment_news.items.items():
            platform_name = increment_news.id_to_name.get(platform_id, platform_id)
            print(f"\n  {platform_name} ({platform_id}): {len(news_list)} 条新增")
            for item in news_list[:5]:  # 只显示前5条
                print(f"    {item.rank}. {item.title[:50]}...")
            if len(news_list) > 5:
                print(f"    ... 还有 {len(news_list) - 5} 条")
    else:
        print(f"\n【增量数据】")
        print("  本次没有新增新闻（所有新闻都已存在于数据库中）")
    
    if full_news and full_news.failed_ids:
        print(f"\n【失败的平台】")
        for failed_id in full_news.failed_ids:
            print(f"  - {failed_id}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()


