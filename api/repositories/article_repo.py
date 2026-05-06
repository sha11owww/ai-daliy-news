from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class ArticleRepository:
    """文章数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def batch_insert(self, articles: list[dict]) -> list[int]:
        """批量插入文章，重复 URL 则更新 raw_content"""
        if not articles:
            return []
        stmt = """
            INSERT INTO articles (title, url, source, source_id, raw_content, status, metadata)
            VALUES (:title, :url, :source, :source_id, :raw_content, 'raw', CAST(:metadata AS JSONB))
            ON CONFLICT (url) DO UPDATE SET raw_content = EXCLUDED.raw_content
            RETURNING id
        """
        result = await self.session.execute(text(stmt), articles)
        await self.session.commit()
        return [row[0] for row in result.fetchall()]

    async def get_unprocessed(self, limit: int = 50) -> list[dict]:
        """获取待处理的原始文章（status = 'raw'）"""
        stmt = """
            SELECT id, title, url, source, raw_content, cleaned_text
            FROM articles
            WHERE status = 'raw'
            ORDER BY id ASC
            LIMIT :limit
        """
        result = await self.session.execute(text(stmt), {"limit": limit})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def update_article(self, article_id: int, updates: dict) -> None:
        """更新文章字段"""
        sets = ", ".join(f"{k} = :{k}" for k in updates)
        stmt = f"UPDATE articles SET {sets} WHERE id = :id"
        updates["id"] = article_id
        await self.session.execute(text(stmt), updates)
        await self.session.commit()

    async def get_by_date(self, report_date: date, status: str = "published") -> list[dict]:
        """获取某天的已发布文章"""
        stmt = """
            SELECT * FROM articles
            WHERE published_date = :date AND status = :status
            ORDER BY importance_score DESC
        """
        result = await self.session.execute(text(stmt), {"date": report_date, "status": status})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def get_articles_by_ids(self, ids: list[int]) -> list[dict]:
        """按 ID 列表获取文章"""
        stmt = "SELECT * FROM articles WHERE id = ANY(:ids) ORDER BY importance_score DESC"
        result = await self.session.execute(text(stmt), {"ids": ids})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
