import os
from datetime import date, datetime
from typing import Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import DailyReportState, ArticleState
from agent.tools import scan_sources, fetch_content, write_summary, classify, save_report, select_articles
from agent.tools.saver import _load_seen_urls
from agent.reflection import critique_summary

load_dotenv()

MAX_CRITIQUE_ATTEMPTS = 2


async def collect_node(state: DailyReportState) -> dict:
    articles = await scan_sources()
    return {"raw_articles": articles}


async def select_node(state: DailyReportState) -> dict:
    """节点 2：先过滤已见文章，再 LLM 选文"""
    articles = state.get("raw_articles", [])
    if not articles:
        return {"selected_article_ids": [], "status": "empty"}

    seen = _load_seen_urls()
    fresh = [a for a in articles if a.get("url") not in seen]
    skipped = len(articles) - len(fresh)
    if skipped:
        print(f"[select] 去重: 跳过 {skipped} 篇, 剩余 {len(fresh)} 篇新候选")

    session_type = state.get("session_type", "morning")
    selected = await select_articles(fresh, session_type)
    if not selected:
        print("[select] LLM 未选中任何文章，取前 15 篇兜底")
        selected = fresh[:15]
    return {"selected_article_ids": [id(a) for a in selected], "raw_articles": selected}


async def fetch_node(state: DailyReportState) -> dict:
    articles = state.get("raw_articles", [])
    processed = []
    for a in articles:
        cleaned = a["raw_content"][:2000] if a.get("raw_content") else await fetch_content(a["url"])
        processed.append({
            "id": 0, "title": a["title"], "url": a["url"], "source": a["source"],
            "source_id": a.get("source_id", ""), "raw_content": a.get("raw_content", ""),
            "cleaned_text": cleaned, "summary": None, "brief": None,
            "tags": [], "section": None, "importance_score": 3, "status": "fetched",
            "critique_result": None, "critique_attempts": 0, "metadata": a.get("metadata", {}),
        })
    return {"processed_articles": processed}


async def summarize_node(state: DailyReportState) -> dict:
    arts = state.get("processed_articles", [])
    for a in arts:
        if a["status"] == "fetched":
            a["summary"] = await write_summary(a, style="normal")
            a["brief"] = await write_summary(a, style="brief")
            a["status"] = "summarized"
    return {"processed_articles": arts}


async def reflect_node(state: DailyReportState) -> dict:
    arts = state.get("processed_articles", [])
    for a in arts:
        if a["status"] != "summarized" or not a.get("summary"):
            continue
        r = await critique_summary(a["title"], a["summary"])
        a["critique_result"] = r.get("suggestion", "")
        a["critique_attempts"] = a.get("critique_attempts", 0) + 1
        if not r.get("pass", True) and a["critique_attempts"] < MAX_CRITIQUE_ATTEMPTS:
            a["summary"] = await write_summary(a, style=f"normal（改进：{r.get('suggestion', '')}）")
        a["status"] = "reviewed"
    return {"processed_articles": arts}


async def classify_node(state: DailyReportState) -> dict:
    arts = state.get("processed_articles", [])
    for a in arts:
        if a["status"] != "reviewed":
            continue
        r = await classify(a)
        a["tags"] = r.get("tags", ["ai"])
        a["section"] = r.get("section", "行业重磅")
        a["importance_score"] = r.get("importance_score", 3)
        a["status"] = "classified"
    return {"processed_articles": arts}


FIXED_SECTIONS = ["行业重磅", "技术内核", "AIGC 多模态", "产品应用与工具", "商业政策"]


async def layout_node(state: DailyReportState) -> dict:
    arts = state.get("processed_articles", [])
    today = date.today()
    st = state.get("session_type", "morning")
    prefix = "AI早报" if st == "morning" else "AI晚报"
    title_str = f"{prefix} · {today.strftime('%Y年%m月%d日')}"
    sorted_arts = sorted(arts, key=lambda a: -a["importance_score"])
    sec_arts = {s: [] for s in FIXED_SECTIONS}
    for a in sorted_arts:
        s = a.get("section") or "行业重磅"
        sec_arts[s if s in sec_arts else "行业重磅"].append(a)
    sections, article_ids = [], []
    for sec in FIXED_SECTIONS:
        if sec_arts[sec]:
            sections.append({"name": sec, "article_ids": [a.get("id", 0) for a in sec_arts[sec]]})
            article_ids.extend(a.get("id", 0) for a in sec_arts[sec])
    return {"sections": sections, "article_order": article_ids, "title": title_str,
            "status": "published", "editor_notes": f"自动生成于 {datetime.now()}", "total_articles": len(arts)}


async def save_node(state: DailyReportState) -> dict:
    r = await save_report(state)
    print(f"[save] {r.get('method', '?')} 保存: {r.get('total', 0)} 篇")
    return {"status": "saved"}


def should_reflect(state: DailyReportState) -> Literal["reflect", "classify"]:
    return "reflect" if os.getenv("REFLECTION_ENABLED", "true").lower() == "true" else "classify"


def build_agent():
    builder = StateGraph(DailyReportState)
    for name, fn in [("collect", collect_node), ("select", select_node), ("fetch", fetch_node),
                     ("summarize", summarize_node), ("reflect", reflect_node), ("classify", classify_node),
                     ("layout", layout_node), ("save", save_node)]:
        builder.add_node(name, fn)
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "select")
    builder.add_edge("select", "fetch")
    builder.add_edge("fetch", "summarize")
    builder.add_conditional_edges("summarize", should_reflect)
    builder.add_edge("reflect", "classify")
    builder.add_edge("classify", "layout")
    builder.add_edge("layout", "save")
    builder.add_edge("save", END)
    return builder.compile(checkpointer=MemorySaver())
