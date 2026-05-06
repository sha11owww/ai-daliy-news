from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Article:
    """文章模型"""
    id: Optional[int] = None
    title: str = ""
    url: str = ""
    source: str = ""           # linuxdo/reddit/twitter
    source_id: Optional[str] = None
    raw_content: Optional[str] = None
    cleaned_text: Optional[str] = None
    summary: Optional[str] = None
    brief: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    section: Optional[str] = None
    importance_score: int = 3
    status: str = "raw"
    published_date: Optional[date] = None
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DailyReport:
    """日报模型"""
    id: Optional[int] = None
    report_date: Optional[date] = None
    title: str = ""
    article_order: list[int] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)
    editor_notes: Optional[str] = None
    total_articles: int = 0
    status: str = "draft"
    created_at: Optional[datetime] = None
