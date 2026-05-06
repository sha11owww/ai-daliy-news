from datetime import date
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
    """获取历史日报列表"""
    stmt = """
        SELECT id, report_date, title, total_articles, status, created_at
        FROM daily_reports
        ORDER BY report_date DESC
        LIMIT :limit
    """
    result = await db.execute(text(stmt), {"limit": limit})
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


@router.get("/today")
async def get_today_report(db: AsyncSession = Depends(get_db)):
    """获取今日完整日报（含文章列表）"""
    today = date.today().isoformat()
    stmt = "SELECT * FROM daily_reports WHERE report_date = :today"
    result = await db.execute(text(stmt), {"today": today})
    row = result.fetchone()
    if not row:
        return {"error": "今日日报尚未生成"}, 404
    report = dict(row._mapping)

    # 按顺序获取文章
    art_stmt = """
        SELECT * FROM articles
        WHERE id = ANY(:ids) AND status = 'published'
    """
    art_result = await db.execute(text(art_stmt), {"ids": report["article_order"]})
    articles = [dict(r._mapping) for r in art_result.fetchall()]

    # 保持 Agent 排好的顺序
    id_order = report["article_order"]
    article_map = {a["id"]: a for a in articles}
    report["articles"] = [article_map[i] for i in id_order if i in article_map]
    return report


@router.get("/{report_date}")
async def get_report_by_date(report_date: str, db: AsyncSession = Depends(get_db)):
    """按日期获取指定日报"""
    stmt = "SELECT * FROM daily_reports WHERE report_date = :date"
    result = await db.execute(text(stmt), {"date": report_date})
    row = result.fetchone()
    if not row:
        return {"error": "日报不存在"}, 404
    return dict(row._mapping)
