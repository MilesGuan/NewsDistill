# coding=utf-8
"""
数据模型定义

定义新闻数据的数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class NewsItem:
    """新闻条目数据模型"""

    title: str  # 新闻标题
    platform_id: str  # 平台ID（如 zhihu, weibo）
    platform_name: str = ""  # 平台名称（运行时使用，数据库不存储）
    rank: int = 0  # 排名
    url: str = ""  # 链接 URL
    mobile_url: str = ""  # 移动端 URL
    crawl_time: str = ""  # 抓取时间（HH:MM 格式）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "platform_id": self.platform_id,
            "platform_name": self.platform_name,
            "rank": self.rank,
            "url": self.url,
            "mobile_url": self.mobile_url,
            "crawl_time": self.crawl_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsItem":
        """从字典创建"""
        return cls(
            title=data.get("title", ""),
            platform_id=data.get("platform_id", ""),
            platform_name=data.get("platform_name", ""),
            rank=data.get("rank", 0),
            url=data.get("url", ""),
            mobile_url=data.get("mobile_url", ""),
            crawl_time=data.get("crawl_time", ""),
        )


@dataclass
class NewsData:
    """
    新闻数据集合

    结构:
    - date: 日期（YYYY-MM-DD）
    - crawl_time: 抓取时间（HH:MM）
    - items: 按 platform_id 分组的新闻条目
    - id_to_name: platform_id 到名称的映射
    - failed_ids: 失败的 platform_id 列表
    """

    date: str  # 日期
    crawl_time: str  # 抓取时间
    items: Dict[str, List[NewsItem]]  # 按 platform_id 分组的条目
    id_to_name: Dict[str, str] = field(default_factory=dict)  # ID到名称映射
    failed_ids: List[str] = field(default_factory=list)  # 失败的ID

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        items_dict = {}
        for platform_id, news_list in self.items.items():
            items_dict[platform_id] = [item.to_dict() for item in news_list]

        return {
            "date": self.date,
            "crawl_time": self.crawl_time,
            "items": items_dict,
            "id_to_name": self.id_to_name,
            "failed_ids": self.failed_ids,
        }

#同类NewsItem聚合成一条
@dataclass
class MergedNewsItem:
    title: str  # ai聚合后的标题
    news: List[NewsItem]


@dataclass
class NewsCategory:
    category: str  # ai聚合的分类
    items: List[MergedNewsItem]
