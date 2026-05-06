from datetime import date
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/")
async def list_reports(
    limit: int = Query(default=30, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取历史日报列表（含 session_type）"""
    stmt = """
        SELECT id, report_date, session_type, title, total_articles, status, created_at
        FROM daily_reports
        ORDER BY report_date DESC, session_type DESC
        LIMIT :limit
    """
    result = await db.execute(text(stmt), {"limit": limit})
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


@router.get("/today")
async def get_today_reports(db: AsyncSession = Depends(get_db)):
    """获取今日所有日报（早报+晚报）"""
    today = date.today()
    stmt = "SELECT * FROM daily_reports WHERE report_date = :today ORDER BY session_type"
    result = await db.execute(text(stmt), {"today": today})
    rows = result.fetchall()
    if not rows:
        return {"morning": None, "evening": None}

    reports = {}
    for row in rows:
        report = dict(row._mapping)
        art_stmt = """
            SELECT * FROM articles
            WHERE id = ANY(:ids) AND status = 'published'
        """
        art_result = await db.execute(text(art_stmt), {"ids": report["article_order"]})
        articles = [dict(r._mapping) for r in art_result.fetchall()]
        id_order = report["article_order"]
        article_map = {a["id"]: a for a in articles}
        report["articles"] = [article_map[i] for i in id_order if i in article_map]
        reports[report["session_type"]] = report

    return {"morning": reports.get("morning"), "evening": reports.get("evening")}


@router.get("/today/morning")
async def get_today_morning_report(db: AsyncSession = Depends(get_db)):
    """获取今日早报"""
    today = date.today()
    stmt = "SELECT * FROM daily_reports WHERE report_date = :today AND session_type = 'morning'"
    result = await db.execute(text(stmt), {"today": today})
    row = result.fetchone()
    if not row:
        return {"error": "今日早报尚未生成"}, 404
    report = dict(row._mapping)
    art_stmt = "SELECT * FROM articles WHERE id = ANY(:ids) AND status = 'published'"
    art_result = await db.execute(text(art_stmt), {"ids": report["article_order"]})
    articles = [dict(r._mapping) for r in art_result.fetchall()]
    id_order = report["article_order"]
    article_map = {a["id"]: a for a in articles}
    report["articles"] = [article_map[i] for i in id_order if i in article_map]
    return report


@router.get("/today/evening")
async def get_today_evening_report(db: AsyncSession = Depends(get_db)):
    """获取今晚晚报"""
    today = date.today()
    stmt = "SELECT * FROM daily_reports WHERE report_date = :today AND session_type = 'evening'"
    result = await db.execute(text(stmt), {"today": today})
    row = result.fetchone()
    if not row:
        return {"error": "今日晚报尚未生成"}, 404
    report = dict(row._mapping)
    art_stmt = "SELECT * FROM articles WHERE id = ANY(:ids) AND status = 'published'"
    art_result = await db.execute(text(art_stmt), {"ids": report["article_order"]})
    articles = [dict(r._mapping) for r in art_result.fetchall()]
    id_order = report["article_order"]
    article_map = {a["id"]: a for a in articles}
    report["articles"] = [article_map[i] for i in id_order if i in article_map]
    return report


@router.get("/calendar")
async def get_calendar(
    year: int = Query(default=None),
    month: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """获取日历数据：返回指定月份哪些日期有日报"""
    today = date.today()
    y = year or today.year
    m = month or today.month

    start_date = date(y, m, 1)
    if m == 12:
        end_date = date(y + 1, 1, 1)
    else:
        end_date = date(y, m + 1, 1)

    stmt = """
        SELECT report_date, session_type
        FROM daily_reports
        WHERE status = 'published'
          AND report_date >= :start AND report_date < :end
        ORDER BY report_date DESC, session_type
    """
    result = await db.execute(text(stmt), {"start": start_date, "end": end_date})
    rows = result.fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.report_date)].append(row.session_type)
    return [{"date": d, "sessions": sorted(set(v))} for d, v in grouped.items()]


@router.get("/{report_date}/{session}")
async def get_report_by_date_and_session(
    report_date: str,
    session: str,
    db: AsyncSession = Depends(get_db),
):
    """按日期+时段获取日报"""
    if session not in ("morning", "evening"):
        return {"error": "时段参数无效，使用 morning 或 evening"}, 400
    try:
        parsed_date = date.fromisoformat(report_date)
    except ValueError:
        return {"error": "日期格式无效，请使用 YYYY-MM-DD"}, 400

    stmt = "SELECT * FROM daily_reports WHERE report_date = :date AND session_type = :st"
    result = await db.execute(text(stmt), {"date": parsed_date, "st": session})
    row = result.fetchone()
    if not row:
        return {"error": f"{report_date} {session}日报不存在"}, 404
    report = dict(row._mapping)
    art_stmt = "SELECT * FROM articles WHERE id = ANY(:ids) AND status = 'published'"
    art_result = await db.execute(text(art_stmt), {"ids": report["article_order"]})
    articles = [dict(r._mapping) for r in art_result.fetchall()]
    id_order = report["article_order"]
    article_map = {a["id"]: a for a in articles}
    report["articles"] = [article_map[i] for i in id_order if i in article_map]
    return report


@router.get("/{report_date}")
async def get_report_by_date(report_date: str, db: AsyncSession = Depends(get_db)):
    """按日期获取该日所有日报"""
    try:
        parsed_date = date.fromisoformat(report_date)
    except ValueError:
        return {"error": "日期格式无效，请使用 YYYY-MM-DD"}, 400
    stmt = "SELECT * FROM daily_reports WHERE report_date = :date ORDER BY session_type"
    result = await db.execute(text(stmt), {"date": parsed_date})
    rows = result.fetchall()
    if not rows:
        return {"error": "日报不存在"}, 404
    reports = []
    for row in rows:
        report = dict(row._mapping)
        art_stmt = "SELECT * FROM articles WHERE id = ANY(:ids) AND status = 'published'"
        art_result = await db.execute(text(art_stmt), {"ids": report["article_order"]})
        articles = [dict(r._mapping) for r in art_result.fetchall()]
        id_order = report["article_order"]
        article_map = {a["id"]: a for a in articles}
        report["articles"] = [article_map[i] for i in id_order if i in article_map]
        reports.append(report)
    return reports
