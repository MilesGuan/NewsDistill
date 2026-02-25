from html import escape
import json
from datetime import date
from pathlib import Path

from db.models import NewsCategory, MergedNewsItem, NewsItem


# 用分组 news 数据生成可读的 HTML 字符串
# 要求：美观简洁，适合移动端阅读
def generate_html(categories: list[NewsCategory]) -> str:
    # 使用字符串列表累积 HTML 片段，最后一次性 join，性能好且简单
    parts: list[str] = []

    # 文档头与基础结构
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="zh-CN">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8">')
    parts.append(
        '<meta name="viewport" content="width=device-width, initial-scale=1, '
        "maximum-scale=1, minimum-scale=1, viewport-fit=cover"
        '">'
    )
    parts.append("<title>新闻精读</title>")

    # 页面样式：整体浅色背景，内容区域居中，分类为暖色胶囊，平台为蓝色小标签
    # 尽量减少多余装饰，保证在手机上阅读舒适
    parts.append(
        "<style>"
        "body{margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"
        '"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans","PingFang SC",'
        '"Hiragino Sans GB","Microsoft YaHei",sans-serif;'
        "background:#f5f7fb;color:#222;font-size:15px;line-height:1.6;}"
        ".page{max-width:720px;margin:0 auto;padding:10px 12px 28px;}"
        ".category{margin:14px 0 4px;}"
        ".category-title{font-size:15px;font-weight:600;margin:8px 0 6px;"
        "padding:5px 10px;border-radius:999px;display:inline-block;"
        "background:#fff3e0;border:1px solid #fed7aa;color:#c05621;}"
        ".news-list{list-style:none;margin:4px 0 0;padding:0;}"
        ".news-item{background:#ffffff;border-radius:10px;padding:8px 10px;"
        "margin:6px 0;box-shadow:0 1px 3px rgba(15,23,42,0.05);}"
        ".news-title{font-size:15px;font-weight:500;margin:0;"
        "word-break:break-all;display:flex;flex-wrap:wrap;"
        "align-items:center;column-gap:4px;row-gap:2px;}"
        ".news-text{flex:0 1 auto;}"
        ".sources{display:flex;flex-wrap:wrap;gap:4px;}"
        ".source-tag{font-size:12px;padding:2px 7px;border-radius:999px;"
        "background:#e5f1ff;color:#1d4ed8;text-decoration:none;}"
        ".source-tag:active{opacity:0.75;}"
        "a{color:inherit;}"
        "</style>"
    )
    parts.append("</head>")
    parts.append("<body>")
    # 主体容器，控制最大宽度与边距
    parts.append('<div class="page">')

    # 遍历每个分类块
    for category in categories:
        if not category.items:
            continue

        cat_name = escape(category.category or "")
        parts.append('<section class="category">')
        parts.append(f'<div class="category-title">{cat_name}</div>')
        parts.append('<ul class="news-list">')

        # 每个 MergedNewsItem 是一条聚合后的“新闻”
        for merged in category.items:
            title = escape(merged.title or "")
            parts.append('<li class="news-item">')
            # 标题 + 平台标签放在同一个 flex 行内，标签可以紧贴标题文本
            parts.append('<div class="news-title">')
            parts.append(f'<span class="news-text">{title}</span>')

            if merged.news:
                # 平台列表：每个平台渲染一个可点击的小标签
                parts.append('<span class="sources">')
                for n in merged.news:
                    platform_name = n.platform_name or n.platform_id or ""
                    label = f"【{platform_name}】"
                    label_escaped = escape(label)

                    # 优先使用移动端链接，缺省时退回到普通 URL
                    url = n.mobile_url or n.url or ""
                    # 所有平台的标签都支持跳转
                    if url:
                        href = escape(url, quote=True)
                        parts.append(
                            f'<a class="source-tag" href="{href}" '
                            'target="_blank" rel="noopener noreferrer">'
                            f"{label_escaped}</a>"
                        )
                    else:
                        # 无链接时仅展示平台标签
                        parts.append(
                            f'<span class="source-tag">{label_escaped}</span>'
                        )

                parts.append("</span>")  # .sources

            parts.append("</div>")  # .news-title
            parts.append("</li>")

        parts.append("</ul>")
        parts.append("</section>")

    parts.append("</div>")  # .page
    parts.append("</body>")
    parts.append("</html>")

    return "".join(parts)


if __name__ == "__main__":
    # 从 test/categories.txt 反序列化为 NewsCategory 列表，
    # 调用 generate_html(categories) 并写入文件，路径为 output/html/[当前日期].html。
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

    html_content = generate_html(categories)

    html_dir = project_root / "output" / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    today_str = date.today().strftime("%Y-%m-%d")
    output_path = html_dir / f"{today_str}.html"
    output_path.write_text(html_content, encoding="utf-8")

