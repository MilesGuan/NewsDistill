# 和大语言模型交互用到的model
from dataclasses import dataclass
from typing import List, Dict
from pydantic import BaseModel, Field


@dataclass
class AINewsItem:
    id: int
    title: str  # 新闻标题


@dataclass
class AINewsData:
    items: Dict[str, List[AINewsItem]]  # 按 platform_id 分组的条目


class AIOutputNewsItem(BaseModel):
    title: str = Field(
        description="新闻标题"
    )
    ids: List[int] = Field(
        description="被聚合的新闻id"
    )

class AIFilterOutput(BaseModel):
    items: List[AIOutputNewsItem] = Field(
        description="筛选聚合后的结果列表"
    )

class AIOutputCategory(BaseModel):
    category: str = Field(
        description="新闻分类名称"
    )
    items: List[AIOutputNewsItem]


class AIOutputModel(BaseModel):
    digest: str = Field(
        description="对最核心的一到两个新闻做个摘要，不超过25字"
    )
    items: List[AIOutputCategory] = Field(
        description="按分类聚合后的新闻结果"
    )


@dataclass
class AIErrorOutput:
    error_msgs: List[str]
