import os
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ainews")

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session() as session:
        yield session


async def init_db():
    """验证数据库连接是否正常"""
    async with engine.begin() as conn:
        await conn.execute(sa.text("SELECT 1"))
    print("数据库连接成功")


async def run_migrations():
    """执行 schema.sql 建表语句

    逐条执行 SQL 语句，正确处理 PL/pgSQL 函数定义中的美元引号。
    """
    dir_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
    with open(dir_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # 按分号拆分，但忽略美元引号($$...$$)内的分号
    statements = []
    current = []
    in_dollar = False
    for line in sql.split("\n"):
        if "$$" in line:
            in_dollar = not in_dollar
        current.append(line)
        if not in_dollar and line.strip().endswith(";"):
            statements.append("\n".join(current))
            current = []

    if current:
        statements.append("\n".join(current))

    async with engine.begin() as conn:
        for stmt in statements:
            stripped = stmt.strip()
            if stripped:
                await conn.exec_driver_sql(stripped)

    # 数据迁移：给旧表加 session_type 字段
    migration = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'daily_reports' AND column_name = 'session_type'
        ) THEN
            ALTER TABLE daily_reports ADD COLUMN session_type VARCHAR(10) NOT NULL DEFAULT 'morning';
        END IF;

        IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'daily_reports'::regclass
            AND conname = 'daily_reports_report_date_key'
        ) THEN
            ALTER TABLE daily_reports DROP CONSTRAINT daily_reports_report_date_key;
        END IF;
    END
    $$;
    """
    async with engine.begin() as conn:
        await conn.exec_driver_sql(migration)

    print("数据库迁移完成")
