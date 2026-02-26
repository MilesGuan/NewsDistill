from core.data_fetch import fetch_news
from core.news_processor import parse_news, llm_distill, merge_categories
from core.yaml_utils import get_sources_platform_ids
from notifier import feishu_notifier


# 全量新闻处理
def full_news_task(only_increment: bool = True):
    platform_ids = get_sources_platform_ids()
    todo_news = fetch_news(platform_ids, only_increment=only_increment)
    if not todo_news:
        return []

    news_json, id_to_news_item = parse_news(todo_news)
    ai_result, used_model_name, error_messages = llm_distill(news_json)

    # 由调用方统一打印实际使用模型和错误信息
    if ai_result is None:
        print("所有模型调用失败，错误汇总：")
        for em in error_messages:
            print(em)
        return []

    print(f"本次实际使用的大模型为: {used_model_name}")
    categories = merge_categories(ai_result, id_to_news_item)
    feishu_notifier.send_news_results_to_feishu(categories)
    return categories


if __name__ == '__main__':
    full_news_task()
