from typing import TypedDict, Optional, Annotated
from operator import add


class ArticleState(TypedDict):
    """文章中继状态：记录每篇文章在 Agent 流程中的处理结果"""
    id: int
    title: str
    url: str
    source: str
    source_id: str
    raw_content: Optional[str]
    cleaned_text: Optional[str]
    summary: Optional[str]
    brief: Optional[str]
    tags: list[str]
    section: Optional[str]
    importance_score: int
    status: str
    critique_result: Optional[str]
    critique_attempts: int
    metadata: dict


class DailyReportState(TypedDict):
    """日报状态：LangGraph 工作流的全局状态"""
    report_date: str
    title: str
    raw_articles: list[dict]
    processed_articles: Annotated[list[ArticleState], add]
    selected_article_ids: list[int]
    sections: list[dict]
    editor_notes: str
    status: str
