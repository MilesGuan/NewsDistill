from core.data_fetch import fetch_news
from core.news_processor import parse_news, llm_distill, merge_categories
from core.yaml_utils import get_sources_platform_ids
from notifier import feishu_notifier
from datetime import datetime


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
    feishu_notifier.send_news_results_to_feishu(title, categories)
    print("本次task执行完成")


if __name__ == '__main__':
    news_task()
