import json, os
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.database import get_db

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("/")
async def list_articles(
    report_date: str = Query(default=None),
    source: str = Query(default=None),
    section: str = Query(default=None),
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
):
    conditions = ["status = 'published'"]
    params = {}
    if report_date:
        conditions.append("published_date = :date")
        params["date"] = date.fromisoformat(report_date)
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
    return [dict(row._mapping) for row in result.fetchall()]


@router.get("/by-url")
async def get_article_by_url(url: str = Query(...)):
    """通过 URL 在 JSON 日报文件中查找文章"""
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports"))
    today = date.today()
    for i in range(7):
        d = today - timedelta(days=i)
        for session in ("morning", "evening"):
            path = os.path.join(base, d.isoformat(), f"{session}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for a in json.load(f).get("articles", []):
                            if a.get("url") == url:
                                return a
                except Exception:
                    pass
    return {"error": "文章不存在"}, 404


@router.get("/{article_id}")
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    stmt = "SELECT * FROM articles WHERE id = :id"
    result = await db.execute(text(stmt), {"id": article_id})
    row = result.fetchone()
    if not row:
        return {"error": "文章不存在"}, 404
    return dict(row._mapping)
