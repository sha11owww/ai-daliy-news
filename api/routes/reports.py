from datetime import date
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/")
async def list_reports(limit: int = Query(default=30, le=100), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        text("SELECT id,report_date,session_type,title,total_articles,status,created_at FROM daily_reports ORDER BY report_date DESC, session_type DESC LIMIT :limit"),
        {"limit": limit})).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/today")
async def get_today_reports(db: AsyncSession = Depends(get_db)):
    today = date.today()
    db_rows = (await db.execute(
        text("SELECT * FROM daily_reports WHERE report_date=:today ORDER BY session_type"),
        {"today": today})).fetchall()
    if db_rows:
        reports = {}
        for row in db_rows:
            r = dict(row._mapping)
            arts = (await db.execute(
                text("SELECT * FROM articles WHERE id=ANY(:ids) AND status='published'"),
                {"ids": r["article_order"]})).fetchall()
            amap = {a["id"]: dict(a._mapping) for a in arts}
            r["articles"] = [amap[i] for i in r["article_order"] if i in amap]
            reports[r["session_type"]] = r
        return {"morning": reports.get("morning"), "evening": reports.get("evening")}
    # 本地 JSON 兜底
    return _load_from_json(today)


def _load_from_json(report_date: date) -> dict:
    import json, os
    date_str = report_date.isoformat()
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports"))
    result = {"morning": None, "evening": None}
    for s in ("morning", "evening"):
        p = os.path.join(base, date_str, f"{s}.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
                d["session_type"] = s
                result[s] = d
    return result


@router.get("/calendar")
async def get_calendar(year: int = Query(default=None), month: int = Query(default=None), db: AsyncSession = Depends(get_db)):
    today = date.today()
    y = year or today.year
    m = month or today.month
    start_date = date(y, m, 1)
    end_date = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    rows = (await db.execute(
        text("SELECT report_date,session_type FROM daily_reports WHERE status='published' AND report_date>=:start AND report_date<:end ORDER BY report_date DESC,session_type"),
        {"start": start_date, "end": end_date})).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.report_date)].append(row.session_type)
    return [{"date": d, "sessions": sorted(set(v))} for d, v in grouped.items()]


@router.get("/{report_date}/{session}")
async def get_report_by_date_and_session(report_date: str, session: str, db: AsyncSession = Depends(get_db)):
    if session not in ("morning", "evening"):
        return {"error":"invalid session"},400
    try:
        parsed_date = date.fromisoformat(report_date)
    except ValueError:
        return {"error":"invalid date"},400
    row = (await db.execute(
        text("SELECT * FROM daily_reports WHERE report_date=:date AND session_type=:st"),
        {"date": parsed_date, "st": session})).fetchone()
    if not row:
        data = _load_from_json(parsed_date).get(session)
        if data:
            return data
        return {"error":"not found"},404
    r = dict(row._mapping)
    arts = (await db.execute(
        text("SELECT * FROM articles WHERE id=ANY(:ids) AND status='published'"),
        {"ids": r["article_order"]})).fetchall()
    amap = {a["id"]: dict(a._mapping) for a in arts}
    r["articles"] = [amap[i] for i in r["article_order"] if i in amap]
    return r


@router.get("/{report_date}")
async def get_report_by_date(report_date: str, db: AsyncSession = Depends(get_db)):
    try:
        parsed_date = date.fromisoformat(report_date)
    except ValueError:
        return {"error":"invalid date"},400
    rows = (await db.execute(
        text("SELECT * FROM daily_reports WHERE report_date=:date ORDER BY session_type"),
        {"date": parsed_date})).fetchall()
    if not rows:
        json_result = _load_from_json(parsed_date)
        reports = [json_result[s] for s in ("morning","evening") if json_result.get(s)]
        return reports if reports else ({"error":"not found"},404)
    reports = []
    for row in rows:
        r = dict(row._mapping)
        arts = (await db.execute(
            text("SELECT * FROM articles WHERE id=ANY(:ids) AND status='published'"),
            {"ids": r["article_order"]})).fetchall()
        amap = {a["id"]: dict(a._mapping) for a in arts}
        r["articles"] = [amap[i] for i in r["article_order"] if i in amap]
        reports.append(r)
    return reports
