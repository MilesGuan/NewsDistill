from core.data_fetch import fetch_news
from core.news_processor import parse_news, llm_distill, merge_categories
from core.yaml_utils import get_sources_platform_ids
from notifier import feishu_notifier
from datetime import datetime
from pathlib import Path

from db.models import NewsSummary
from db.database import NewsDatabase


def news_task(only_increment: bool = True):
    now = datetime.now()
    print("="*30)
    print(f"news_task开始，当前时间 {now.strftime('%Y-%m-%d %H:%M:%S')}")
    platform_ids = get_sources_platform_ids()
    todo_news = fetch_news(platform_ids, only_increment=only_increment)
    if not todo_news:
        print("没有新的资讯新闻")
        return
    news_json, id_to_news_item = parse_news(todo_news)
    ai_result, error_output = llm_distill(news_json)

    if ai_result is None:
        print("所有模型调用失败，错误汇总：")
        for em in (error_output.error_msgs if error_output else []):
            print(em)
        return

    title, categories = merge_categories(ai_result, id_to_news_item)

    # 将 AIOutputModel 落库为 NewsSummary（按月分库）
    today = now.strftime("%Y-%m-%d")
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    news_summary = NewsSummary(digest=ai_result.digest, summary=ai_result.summary, update_time=update_time)

    project_root = Path(__file__).resolve().parent.parent
    db_month = f"{now.year}-{now.month}"
    month_db_path = project_root / "output" / "db" / f"{db_month}.db"

    # 若 db 文件已存在但非有效 SQLite 格式，删除后重建
    if month_db_path.exists():
        try:
            with open(month_db_path, "rb") as f:
                header = f.read(16)
            if not header.startswith(b"SQLite format 3\x00"):
                month_db_path.unlink()
        except Exception:
            month_db_path.unlink()

    db = NewsDatabase(db_path=str(month_db_path))
    saved = db.save_summary(today, news_summary)
    if saved:
        print(f"[数据库] 摘要已写入: {month_db_path} (date={today})")
    else:
        print(f"[数据库] 摘要写入失败: {month_db_path} (date={today})")

    feishu_notifier.send_news_results_to_feishu(title, categories)
    print("本次task执行完成")


if __name__ == '__main__':
    news_task()
