import json
from dataclasses import asdict
from pathlib import Path

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider

import envUtils
from core import model_provider
from core.data_fetch import fetch_news
from core.llm_models import AINewsData, AINewsItem, AIOutputModel
from pydantic_ai import Agent, ModelSettings

from db.models import NewsData, NewsCategory, MergedNewsItem

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "config" / "news_prompt.md"


# 1 NewsData中所有NewsItem 生成一个唯一序号id，转换为AINewsItem
# 2 NewsData生成一个AINewsData
# 3 返回AINewsData的json和 id 到原始 NewsItem 的映射
def parse_news(news_data: NewsData):
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


def news_distill(json: str) -> AIOutputModel:
    print(f"大模型处理开始...   传入数据={json}")
    model = model_provider.qwen_plus
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    agent = Agent(
        model,
        system_prompt=system_prompt,
        output_type=AIOutputModel,
        # model_settings=ModelSettings(
        #     # 仅对千问生效
        #     extra_body={
        #         "enable_thinking": True,
        #         "enable_search": False
        #     }
        # )
    )
    _result = agent.run_sync(user_prompt=json)
    print(f"大模型处理完成   {_result.usage()}")
    return _result.output


# 全量新闻处理
def full_news_task():
    platform_ids = [
        "toutiao",  # 今日头条
        "thepaper",  # 澎湃新闻
        # "ifeng",  # 凤凰网
        "cankaoxiaoxi",  # 参考消息
        "sputniknewscn",  # 卫星通讯社
        "zaobao",  # 联合早报
        # "mktnews",  # MKT新闻
        # "kaopu",  # 靠谱新闻
        # "tencent-hot",  # 腾讯新闻 综合早报
        # "wallstreetcn-hot",  # 华尔街见闻 最热
        # "wallstreetcn-quick",  # 华尔街见闻 快讯
        # "wallstreetcn-news",  # 华尔街见闻 最新
        # "cls-hot",  # 财联社热门
        # "cls-telegraph",  # 财联社 电报
        # "cls-depth",  # 财联社 深度
        # "gelonghui",  # 格隆汇
        # "jin10",  # 金十数据
        # "fastbull",  # 快讯通
        # "fastbull-express",  # 法布财经 快讯
        # "fastbull-news",  # 法布财经 头条
        # "ithome",  # IT之家
        # "juejin",  # 掘金
        # "hackernews",  # Hacker News
        # "solidot",  # Solidot
        # "sspai",  # 少数派
    ]
    full_news, increment_news = fetch_news(platform_ids)
    if not full_news:
        return []

    news_json, id_to_news_item = parse_news(full_news)
    ai_result = news_distill(news_json)
    print(json.dumps(ai_result.model_dump(), ensure_ascii=False))

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

    print(json.dumps([asdict(c) for c in categories], ensure_ascii=False))
    return categories


if __name__ == '__main__':
    full_news_task()
