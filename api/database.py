import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ainews")

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """验证数据库连接是否正常"""
    import sqlalchemy as sa
    async with engine.begin() as conn:
        await conn.execute(sa.text("SELECT 1"))
    print("数据库连接成功")


async def run_migrations():
    """执行 schema.sql 建表语句"""
    import os
    import sqlalchemy as sa
    dir_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
    with open(dir_path, "r") as f:
        sql = f.read()
    async with engine.begin() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(sa.text(stmt))
    print("数据库迁移完成")
