from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class ReportRepository:
    """日报数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report_date: date, title: str) -> int:
        """创建或更新日报"""
        stmt = """
            INSERT INTO daily_reports (report_date, title)
            VALUES (:date, :title)
            ON CONFLICT (report_date) DO UPDATE SET title = EXCLUDED.title
            RETURNING id
        """
        result = await self.session.execute(text(stmt), {"date": report_date, "title": title})
        await self.session.commit()
        return result.scalar_one()

    async def update(self, report_id: int, updates: dict) -> None:
        """更新日报字段"""
        sets = ", ".join(f"{k} = :{k}" for k in updates)
        stmt = f"UPDATE daily_reports SET {sets} WHERE id = :id"
        updates["id"] = report_id
        await self.session.execute(text(stmt), updates)
        await self.session.commit()

    async def get_by_date(self, report_date: date) -> dict | None:
        """按日期获取日报"""
        stmt = "SELECT * FROM daily_reports WHERE report_date = :date"
        result = await self.session.execute(text(stmt), {"date": report_date})
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def list_recent(self, limit: int = 30) -> list[dict]:
        """获取最近日报列表"""
        stmt = """
            SELECT id, report_date, title, total_articles, status, created_at
            FROM daily_reports
            ORDER BY report_date DESC
            LIMIT :limit
        """
        result = await self.session.execute(text(stmt), {"limit": limit})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
