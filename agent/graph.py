import os
from datetime import date, datetime
from typing import Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import DailyReportState
from agent.tools import scan_sources, fetch_content, write_summary, classify, save_report, select_articles
from agent.reflection import critique_summary

load_dotenv()
MAX_CRITIQUE_ATTEMPTS = 2


async def collect_node(state: DailyReportState) -> dict:
    return {"raw_articles": await scan_sources()}


async def select_node(state: DailyReportState) -> dict:
    arts = state.get("raw_articles", [])
    if not arts:
        return {"status": "empty"}
    st = state.get("session_type", "morning")
    sel = await select_articles(arts, st)
    return {"selected_article_ids": [id(a) for a in sel], "raw_articles": sel or arts[:15]}


async def fetch_node(state: DailyReportState) -> dict:
    result = []
    for a in state.get("raw_articles", []):
        c = a["raw_content"][:2000] if a.get("raw_content") else await fetch_content(a["url"])
        result.append({"id": 0, "title": a["title"], "url": a["url"], "source": a["source"],
            "source_id": a.get("source_id", ""), "raw_content": a.get("raw_content", ""),
            "cleaned_text": c, "summary": None, "brief": None, "tags": [], "section": None,
            "importance_score": 3, "status": "fetched", "critique_result": None, "critique_attempts": 0,
            "metadata": a.get("metadata", {})})
    return {"processed_articles": result}


async def summarize_node(state: DailyReportState) -> dict:
    for a in state.get("processed_articles", []):
        if a["status"] == "fetched":
            a["summary"] = await write_summary(a, "normal")
            a["brief"] = await write_summary(a, "brief")
            a["status"] = "summarized"
    return {}


async def reflect_node(state: DailyReportState) -> dict:
    for a in state.get("processed_articles", []):
        if a["status"] != "summarized" or not a.get("summary"):
            continue
        r = await critique_summary(a["title"], a["summary"])
        a["critique_result"] = r.get("suggestion", "")
        a["critique_attempts"] = a.get("critique_attempts", 0) + 1
        if not r.get("pass", True) and a["critique_attempts"] < MAX_CRITIQUE_ATTEMPTS:
            a["summary"] = await write_summary(a, f"normal（改进：{r.get('suggestion', '')}）")
        a["status"] = "reviewed"
    return {}


async def classify_node(state: DailyReportState) -> dict:
    for a in state.get("processed_articles", []):
        if a["status"] != "reviewed":
            continue
        r = await classify(a)
        a["tags"] = r.get("tags", ["ai"])
        a["section"] = r.get("section", "行业重磅")
        a["importance_score"] = r.get("importance_score", 3)
        a["status"] = "classified"
    return {}


FIXED = ["行业重磅", "技术内核", "AIGC 多模态", "产品应用与工具", "商业政策"]


async def layout_node(state: DailyReportState) -> dict:
    arts = sorted(state.get("processed_articles", []), key=lambda a: -a["importance_score"])
    today = date.today()
    st = state.get("session_type", "morning")
    title = f"{'AI早报' if st == 'morning' else 'AI晚报'} · {today.strftime('%Y年%m月%d日')}"
    sm = {s: [] for s in FIXED}
    for a in arts:
        s = a.get("section") or "行业重磅"
        sm[s if s in sm else "行业重磅"].append(a)
    secs, ids = [], []
    for s in FIXED:
        if sm[s]:
            secs.append({"name": s, "article_ids": [a.get("id", 0) for a in sm[s]]})
            ids.extend(a.get("id", 0) for a in sm[s])
    return {"sections": secs, "article_order": ids, "title": title, "status": "published",
            "editor_notes": f"自动生成于 {datetime.now()}", "total_articles": len(arts)}


async def save_node(state: DailyReportState) -> dict:
    r = await save_report(state)
    print(f"[save] {r.get('method', '?')} {r.get('total', 0)} 篇")
    return {}


def should_reflect(state) -> Literal["reflect", "classify"]:
    return "reflect" if os.getenv("REFLECTION_ENABLED", "true").lower() == "true" else "classify"


def build_agent():
    b = StateGraph(DailyReportState)
    for n, f in [("collect", collect_node), ("select", select_node), ("fetch", fetch_node),
                 ("summarize", summarize_node), ("reflect", reflect_node), ("classify", classify_node),
                 ("layout", layout_node), ("save", save_node)]:
        b.add_node(n, f)
    b.add_edge(START, "collect")
    b.add_edge("collect", "select")
    b.add_edge("select", "fetch")
    b.add_edge("fetch", "summarize")
    b.add_conditional_edges("summarize", should_reflect)
    b.add_edge("reflect", "classify")
    b.add_edge("classify", "layout")
    b.add_edge("layout", "save")
    b.add_edge("save", END)
    return b.compile(checkpointer=MemorySaver())
