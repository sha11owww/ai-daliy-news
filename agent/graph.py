import os
from datetime import date, datetime
from typing import Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import DailyReportState, ArticleState
from agent.tools import scan_sources, fetch_content, write_summary, classify
from agent.reflection import critique_summary

load_dotenv()

MAX_CRITIQUE_ATTEMPTS = 2  # 每篇文章最多反思重试 2 次


async def collect_node(state: DailyReportState) -> dict:
    """节点 1：扫描所有数据源获取原始文章"""
    articles = await scan_sources()
    return {"raw_articles": articles}


async def select_node(state: DailyReportState) -> dict:
    """节点 2：Agent 选择要处理的文章"""
    articles = state.get("raw_articles", [])
    if not articles:
        return {"selected_article_ids": [], "status": "empty"}

    # 按热度评分排序，取前 15 篇
    scored = []
    for i, a in enumerate(articles):
        meta = a.get("metadata", {})
        score = 0
        if a["source"] == "reddit":
            score = meta.get("score", 0) or 0
        elif a["source"] == "linuxdo":
            score = meta.get("posts_count", 0) or 0
        scored.append((score, i, a))

    scored.sort(key=lambda x: -x[0])
    selected = scored[:15]
    ids = [s[2] for s in selected]
    return {
        "selected_article_ids": ids,
        "raw_articles": [a for _, _, a in selected],
    }


async def fetch_node(state: DailyReportState) -> dict:
    """节点 3：获取选中文章的完整内容"""
    articles = state.get("raw_articles", [])
    processed = []

    for a in articles:
        if a.get("raw_content"):
            cleaned = a["raw_content"][:2000]
        else:
            cleaned = await fetch_content(a["url"])

        article_state: ArticleState = {
            "id": 0,
            "title": a["title"],
            "url": a["url"],
            "source": a["source"],
            "source_id": a.get("source_id", ""),
            "raw_content": a.get("raw_content", ""),
            "cleaned_text": cleaned,
            "summary": None,
            "brief": None,
            "tags": [],
            "section": None,
            "importance_score": 3,
            "status": "fetched",
            "critique_result": None,
            "critique_attempts": 0,
            "metadata": a.get("metadata", {}),
        }
        processed.append(article_state)

    return {"processed_articles": processed}


async def summarize_node(state: DailyReportState) -> dict:
    """节点 4：为所有文章生成摘要"""
    articles = state.get("processed_articles", [])
    updated = []

    for a in articles:
        if a["status"] != "fetched":
            updated.append(a)
            continue

        summary = await write_summary(a, style="normal")
        brief = await write_summary(a, style="brief")
        a["summary"] = summary
        a["brief"] = brief
        a["status"] = "summarized"
        updated.append(a)

    return {"processed_articles": updated}


async def reflect_node(state: DailyReportState) -> dict:
    """节点 5：自我审查摘要质量，不合格则重写"""
    articles = state.get("processed_articles", [])
    updated = []

    for a in articles:
        if a["status"] != "summarized" or not a.get("summary"):
            updated.append(a)
            continue

        result = await critique_summary(a["title"], a["summary"])
        a["critique_result"] = result.get("suggestion", "")
        a["critique_attempts"] = a.get("critique_attempts", 0) + 1

        if not result.get("pass", True) and a["critique_attempts"] < MAX_CRITIQUE_ATTEMPTS:
            revised = await write_summary(a, style=f"normal（改进：{result.get('suggestion', '')}）")
            a["summary"] = revised
        a["status"] = "reviewed"
        updated.append(a)

    return {"processed_articles": updated}


async def classify_node(state: DailyReportState) -> dict:
    """节点 6：分类和打标签"""
    articles = state.get("processed_articles", [])
    updated = []

    for a in articles:
        if a["status"] != "reviewed":
            updated.append(a)
            continue

        result = await classify(a)
        a["tags"] = result.get("tags", ["ai"])
        a["section"] = result.get("section", "行业重磅")
        a["importance_score"] = result.get("importance_score", 3)
        a["status"] = "classified"
        updated.append(a)

    return {"processed_articles": updated}


FIXED_SECTIONS = ["行业重磅", "技术内核", "AIGC 多模态", "产品应用与工具", "商业政策"]


async def layout_node(state: DailyReportState) -> dict:
    """节点 7：按固定 5 栏目排版"""
    articles = state.get("processed_articles", [])
    today = date.today()
    session_type = state.get("session_type", "morning")
    prefix = "AI早报" if session_type == "morning" else "AI晚报"
    title_str = f"{prefix} · {today.strftime('%Y年%m月%d日')}"

    # 按重要度排序
    sorted_arts = sorted(articles, key=lambda a: -a["importance_score"])

    # 按固定栏目分组
    section_articles = {s: [] for s in FIXED_SECTIONS}
    for a in sorted_arts:
        sec = a.get("section") or "行业重磅"
        if sec in section_articles:
            section_articles[sec].append(a)
        else:
            section_articles["行业重磅"].append(a)

    # 生成栏目结构（只保留有文章的栏目）
    sections = []
    article_ids = []
    for sec in FIXED_SECTIONS:
        sec_arts = section_articles[sec]
        if sec_arts:
            sections.append({"name": sec, "article_ids": [a.get("id", 0) for a in sec_arts]})
            for a in sec_arts:
                article_ids.append(a.get("id", 0))

    return {
        "sections": sections,
        "article_order": article_ids,
        "title": title_str,
        "status": "published",
        "editor_notes": f"自动生成于 {datetime.now()}",
        "total_articles": len(articles),
    }


def should_reflect(state: DailyReportState) -> Literal["reflect", "classify"]:
    """条件边：是否启用反思步骤"""
    if os.getenv("REFLECTION_ENABLED", "true").lower() == "true":
        return "reflect"
    return "classify"


def build_agent() -> StateGraph:
    """构建并编译 LangGraph Agent"""
    builder = StateGraph(DailyReportState)

    # 注册节点
    builder.add_node("collect", collect_node)
    builder.add_node("select", select_node)
    builder.add_node("fetch", fetch_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("reflect", reflect_node)
    builder.add_node("classify", classify_node)
    builder.add_node("layout", layout_node)

    # 构建连接
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "select")
    builder.add_edge("select", "fetch")
    builder.add_edge("fetch", "summarize")
    builder.add_conditional_edges("summarize", should_reflect)
    builder.add_edge("reflect", "classify")
    builder.add_edge("classify", "layout")
    builder.add_edge("layout", END)

    return builder.compile(checkpointer=MemorySaver())
