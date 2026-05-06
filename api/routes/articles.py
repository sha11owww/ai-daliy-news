from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.database import get_db

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("/")
async def list_articles(
    report_date: str = Query(default=None, description="按日期筛选"),
    source: str = Query(default=None, description="按来源筛选"),
    section: str = Query(default=None, description="按栏目筛选"),
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取文章列表，支持多条件筛选"""
    conditions = ["status = 'published'"]
    params = {}

    if report_date:
        conditions.append("published_date = :date")
        params["date"] = report_date
    if source:
        conditions.append("source = :source")
        params["source"] = source
    if section:
        conditions.append("section = :section")
        params["section"] = section

    where = " AND ".join(conditions)
    stmt = f"SELECT * FROM articles WHERE {where} ORDER BY importance_score DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(stmt), params)
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


@router.get("/{article_id}")
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    """获取单篇文章详情"""
    stmt = "SELECT * FROM articles WHERE id = :id"
    result = await db.execute(text(stmt), {"id": article_id})
    row = result.fetchone()
    if not row:
        return {"error": "文章不存在"}, 404
    return dict(row._mapping)
