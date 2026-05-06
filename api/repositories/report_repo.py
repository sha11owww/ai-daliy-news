from datetime import date
import json
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class ReportRepository:
    """日报数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report_date: date, title: str, session_type: str = "morning") -> int:
        """创建或更新日报"""
        stmt = """
            INSERT INTO daily_reports (report_date, session_type, title)
            VALUES (:date, :session_type, :title)
            ON CONFLICT (report_date, session_type) DO UPDATE SET title = EXCLUDED.title
            RETURNING id
        """
        result = await self.session.execute(
            text(stmt),
            {"date": report_date, "session_type": session_type, "title": title},
        )
        await self.session.commit()
        return result.scalar_one()

    async def get_by_date_and_session(self, report_date: date, session_type: str) -> dict | None:
        """按日期和时段获取日报"""
        stmt = """
            SELECT * FROM daily_reports
            WHERE report_date = :date AND session_type = :session_type
        """
        result = await self.session.execute(
            text(stmt),
            {"date": report_date, "session_type": session_type},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def update(self, report_id: int, updates: dict) -> None:
        """更新日报字段（sections 为 JSONB 需序列化）"""
        serialized = {}
        for k, v in updates.items():
            if k == "sections" and isinstance(v, (dict, list)):
                serialized[k] = json.dumps(v, ensure_ascii=False)
            else:
                serialized[k] = v
        sets = ", ".join(f"{k} = :{k}" for k in serialized)
        stmt = f"UPDATE daily_reports SET {sets} WHERE id = :id"
        serialized["id"] = report_id
        await self.session.execute(text(stmt), serialized)
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

    async def get_calendar(self, year: int, month: int) -> list[dict]:
        """获取指定月份每日的报告时段分布"""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        stmt = """
            SELECT report_date, session_type
            FROM daily_reports
            WHERE status = 'published'
              AND report_date >= :start_date AND report_date < :end_date
            ORDER BY report_date DESC, session_type
        """
        result = await self.session.execute(text(stmt), {"start_date": start_date, "end_date": end_date})
        rows = result.fetchall()
        grouped = defaultdict(list)
        for row in rows:
            grouped[str(row.report_date)].append(row.session_type)
        return [{"date": d, "sessions": sorted(set(v))} for d, v in grouped.items()]
