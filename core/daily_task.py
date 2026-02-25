import json
from dataclasses import asdict
from pathlib import Path

from core import model_provider
from core.data_fetch import fetch_news
from core.llm_models import AINewsData, AINewsItem, AIOutputModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

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


def news_distill(news_json: str) -> tuple[AIOutputModel | None, str | None, list[str]]:
    print(f"当前新闻数据===>{news_json}")
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    # 实测会遇到模型失败比如 deepseek 报错 Content Exists Risk ，gemini会限流
    # 按列表顺序依次尝试，直到有一个成功或所有都失败
    models = [
        model_provider.deepseek_model,
        # model_provider.qwen_plus,
    ]

    error_messages: list[str] = []

    for idx, model in enumerate(models):
        model_name = getattr(model, "model_name", str(model))
        print(f"大模型{model_name}处理开始...")
        try:
            agent = Agent(
                model,
                system_prompt=system_prompt,
                output_type=AIOutputModel,
            )
            _result = agent.run_sync(user_prompt=news_json)
            print(_result)
            print(_result.output)
            print(
                f"大模型处理完成 [{model_name}] {_result.usage()}  "
                f"返回结果==>{json.dumps(_result.output.model_dump(), ensure_ascii=False)}"
            )
            # 成功时额外返回实际工作的模型名称，并附带错误信息列表（此时通常为空）
            return _result.output, model_name, error_messages
        except ModelHTTPError as e:
            msg = f"模型调用失败 [{model_name}] ModelHTTPError: {e}"
            # 记录 HTTP 错误日志（不在此处打印），然后尝试下一个兜底模型
            error_messages.append(msg)
        except Exception as e:
            msg = f"模型调用失败 [{model_name}] Unexpected error: {e}"
            # 其他异常同样记录日志（不在此处打印）
            error_messages.append(msg)

    # 所有模型都失败时，将所有错误信息汇总返回，交给调用方处理（打印/告警等）
    return None, None, error_messages


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
    ai_result, used_model_name, error_messages = news_distill(news_json)

    # 由调用方统一打印实际使用模型和错误信息
    if ai_result is None:
        print("所有模型调用失败，错误汇总：")
        for em in error_messages:
            print(em)
        return []

    print(f"本次实际使用的大模型为: {used_model_name}")
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
