import json
from dataclasses import asdict
from pathlib import Path

from core import model_provider
from core.data_fetch import fetch_news
from core.llm_models import (
    AINewsData,
    AINewsItem,
    AIOutputModel,
    AIFilterOutput,
    AIErrorOutput,
)
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

from db.models import NewsData, NewsCategory, MergedNewsItem, NewsItem

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_prompt(file_name: str) -> str:
    path = PROJECT_ROOT / "config" / file_name
    return path.read_text(encoding="utf-8")


# 1 NewsData中所有NewsItem 生成一个唯一序号id，转换为AINewsItem
# 2 NewsData生成一个AINewsData
# 3 返回AINewsData的json和 id 到原始 NewsItem 的映射
def parse_news(news_data: NewsData) -> tuple[str, dict[int, NewsItem]]:
    unique_id = 1
    items_dict = {}
    id_to_news_item = {}
    for platform_id, news_list in news_data.items.items():
        ai_items = []
        for item in news_list:
            ai_item = AINewsItem(id=unique_id, title=item.title)
            id_to_news_item[unique_id] = item
            unique_id += 1
            ai_items.append(ai_item)
        items_dict[platform_id] = ai_items

    ai_news_data = AINewsData(items=items_dict)
    json_str = json.dumps(asdict(ai_news_data), ensure_ascii=False)
    return json_str, id_to_news_item


def _llm_run_with_retry(
        llm_input: str,
        system_prompt: str,
        output_type: type,
) -> tuple[object | None, AIErrorOutput | None]:
    """多模型重试兜底：按列表顺序依次尝试，直到有一个成功或所有都失败。"""
    models = [
        model_provider.deepseek_model,
        model_provider.qwen_plus,
    ]
    error_messages: list[str] = []

    for model in models:
        model_name = getattr(model, "model_name", str(model))
        print(f"大模型{model_name}处理开始...")
        try:
            agent = Agent(
                model,
                system_prompt=system_prompt,
                output_type=output_type,
            )
            _result = agent.run_sync(user_prompt=llm_input)
            print(_result)
            print(_result.output)
            print(
                f"大模型处理完成 [{model_name}] {_result.usage()}  "
                f"返回结果==>{json.dumps(_result.output.model_dump(), ensure_ascii=False)}"
            )
            return _result.output, None
        except ModelHTTPError as e:
            msg = f"模型调用失败 [{model_name}] ModelHTTPError: {e}"
            error_messages.append(msg)
        except Exception as e:
            msg = f"模型调用失败 [{model_name}] Unexpected error: {e}"
            error_messages.append(msg)

    return None, AIErrorOutput(error_msgs=error_messages)


# 让大模型对数据进行聚合/筛选
def llm_distill(news_json: str) -> tuple[AIOutputModel | None, AIErrorOutput | None]:
    print(f"当前新闻数据===>{news_json}")
    print("1 筛选聚合")
    filter_prompt = get_prompt("筛选聚合prompt.md")
    filter_result, filter_error = _llm_run_with_retry(news_json, filter_prompt, AIFilterOutput)
    if filter_error is not None:
        return None, filter_error
    print("2 分类总结")
    prompt = get_prompt("分类prompt.md")
    return _llm_run_with_retry(filter_result.model_dump_json(), prompt, AIOutputModel)


def merge_categories(
        ai_result: AIOutputModel,
        id_to_news_item: dict[int, NewsItem],
):
    categories: list[NewsCategory] = []
    for ai_category in ai_result.items:
        merged_items: list[MergedNewsItem] = []
        for ai_item in ai_category.items:
            original_news = []
            for news_id in ai_item.ids:
                news_item = id_to_news_item.get(news_id)
                if news_item:
                    original_news.append(news_item)
            if not original_news:
                continue
            merged_items.append(MergedNewsItem(title=ai_item.title, news=original_news))
        if merged_items:
            categories.append(NewsCategory(category=ai_category.category, items=merged_items))
    print("数据合并结果  " + json.dumps([asdict(c) for c in categories], ensure_ascii=False))
    return ai_result.digest, categories
