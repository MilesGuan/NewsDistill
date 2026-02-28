import json
from pathlib import Path

from db.models import NewsCategory, MergedNewsItem, NewsItem
from notifier import feishu_notifier, html_generator, email_notifier


def create_test_data() -> list[NewsCategory]:
    project_root = Path(__file__).resolve().parent.parent
    categories_file = project_root / "test" / "categories.txt"

    raw = categories_file.read_text(encoding="utf-8")
    data = json.loads(raw)

    categories: list[NewsCategory] = []
    for cat in data:
        items: list[MergedNewsItem] = []
        for item in cat.get("items", []):
            news_list = [
                NewsItem.from_dict(n) for n in item.get("news", [])
            ]
            items.append(
                MergedNewsItem(
                    title=item.get("title", ""),
                    news=news_list,
                )
            )
        categories.append(
            NewsCategory(
                category=cat.get("category", ""),
                items=items,
            )
        )
    return categories

def test_html():
    categories = create_test_data()
    html_content = html_generator.generate_html(categories)
    html_generator.save_html(html_content)
    result = email_notifier.send_to_myself(
        subject='测试',
        from_name='NewsDistill',
        html_content=html_content
    )
    if result:
        print("测试邮件发送成功！")
    else:
        print("测试邮件发送失败！")


def test_feishu_text():
    feishu_notifier.send_feishu_text("一二三四五六七八九十一二三四五六七八九十一二三四五六七八九十一二三四五六七八九十","hahahhaa")

def test_feishu_categories():
    categories = create_test_data()
    feishu_notifier.send_news_results_to_feishu(categories)