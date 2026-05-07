from datetime import date
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/")
async def list_reports(limit: int = Query(default=30, le=100), db: AsyncSession = Depends(get_db)):
    stmt = """SELECT id, report_date, session_type, title, total_articles, status, created_at
        FROM daily_reports ORDER BY report_date DESC, session_type DESC LIMIT :limit"""
    result = await db.execute(text(stmt), {"limit": limit})
    return [dict(row._mapping) for row in result.fetchall()]


@router.get("/today")
async def get_today_reports(db: AsyncSession = Depends(get_db)):
    today = date.today()
    stmt = "SELECT * FROM daily_reports WHERE report_date = :today ORDER BY session_type"
    result = await db.execute(text(stmt), {"today": today})
    rows = result.fetchall()
    if rows:
        reports = {}
        for row in rows:
            report = dict(row._mapping)
            art_result = await db.execute(
                text("SELECT * FROM articles WHERE id = ANY(:ids) AND status = 'published'"),
                {"ids": report["article_order"]})
            articles = [dict(r._mapping) for r in art_result.fetchall()]
            id_order = report["article_order"]
            article_map = {a["id"]: a for a in articles}
            report["articles"] = [article_map[i] for i in id_order if i in article_map]
            reports[report["session_type"]] = report
        return {"morning": reports.get("morning"), "evening": reports.get("evening")}
    return _load_from_json(today)


def _load_from_json(report_date: date) -> dict:
    import json, os
    date_str = report_date.isoformat()
    result = {"morning": None, "evening": None}
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports"))
    local = {}
    for s in ("morning", "evening"):
        p = os.path.join(base, date_str, f"{s}.json")
        local[s] = p
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
                d["session_type"] = s
                result[s] = d

    # 本地已有数据则跳过 GitHub
    if result["morning"] is not None:
        return result

    for s in ("morning", "evening"):
        try:
            import httpx
            r = httpx.get(
                f"https://raw.githubusercontent.com/sha11owww/ai-daliy-news/main/data/reports/{date_str}/{s}.json",
                timeout=1)
            if r.status_code == 200:
                d = r.json()
                d["session_type"] = s
                result[s] = d
                os.makedirs(os.path.dirname(local[s]), exist_ok=True)
                with open(local[s], "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return result


@router.get("/calendar")
async def get_calendar(year: int = Query(default=None), month: int = Query(default=None), db: AsyncSession = Depends(get_db)):
    today = date.today()
    y = year or today.year
    m = month or today.month
    start_date = date(y, m, 1)
    end_date = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    result = await db.execute(
        text("SELECT report_date, session_type FROM daily_reports WHERE status='published' AND report_date>=:start AND report_date<:end ORDER BY report_date DESC, session_type"),
        {"start": start_date, "end": end_date})
    rows = result.fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.report_date)].append(row.session_type)
    # 也扫 JSON 文件补充
    import os
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports"))
    for i in range(7):
        d = today.isoformat()
        for s in ("morning", "evening"):
            p = os.path.join(base, d, f"{s}.json")
            if os.path.exists(p) and d not in grouped:
                grouped[d] = []
            if os.path.exists(p) and s not in grouped.get(d, []):
                grouped[d].append(s)
    return [{"date": d, "sessions": sorted(set(v))} for d, v in grouped.items()]


@router.get("/{report_date}/{session}")
async def get_report_by_date_and_session(report_date: str, session: str, db: AsyncSession = Depends(get_db)):
    if session not in ("morning", "evening"):
        return {"error": "时段参数无效"}, 400
    try:
        parsed_date = date.fromisoformat(report_date)
    except ValueError:
        return {"error": "日期格式无效"}, 400
    result = await db.execute(
        text("SELECT * FROM daily_reports WHERE report_date=:date AND session_type=:st"),
        {"date": parsed_date, "st": session})
    row = result.fetchone()
    if not row:
        data = _load_from_json(parsed_date).get(session)
        if data:
            return data
        return {"error": "日报不存在"}, 404
    report = dict(row._mapping)
    art_result = await db.execute(
        text("SELECT * FROM articles WHERE id=ANY(:ids) AND status='published'"),
        {"ids": report["article_order"]})
    articles = [dict(r._mapping) for r in art_result.fetchall()]
    id_order = report["article_order"]
    article_map = {a["id"]: a for a in articles}
    report["articles"] = [article_map[i] for i in id_order if i in article_map]
    return report


@router.get("/{report_date}")
async def get_report_by_date(report_date: str, db: AsyncSession = Depends(get_db)):
    try:
        parsed_date = date.fromisoformat(report_date)
    except ValueError:
        return {"error": "日期格式无效"}, 400
    result = await db.execute(
        text("SELECT * FROM daily_reports WHERE report_date=:date ORDER BY session_type"),
        {"date": parsed_date})
    rows = result.fetchall()
    if not rows:
        json_result = _load_from_json(parsed_date)
        reports = [json_result[s] for s in ("morning", "evening") if json_result.get(s)]
        return reports if reports else ({"error": "日报不存在"}, 404)
    reports = []
    for row in rows:
        report = dict(row._mapping)
        art_result = await db.execute(
            text("SELECT * FROM articles WHERE id=ANY(:ids) AND status='published'"),
            {"ids": report["article_order"]})
        articles = [dict(r._mapping) for r in art_result.fetchall()]
        id_order = report["article_order"]
        article_map = {a["id"]: a for a in articles}
        report["articles"] = [article_map[i] for i in id_order if i in article_map]
        reports.append(report)
    return reports
