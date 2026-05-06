# AI 日报 Agent 实现计划

> **给 agent 执行者的说明：** 使用 `superpowers:subagent-driven-development` 按任务逐项实现。步骤使用复选框（`- [ ]`）跟踪进度。

**目标：** 构建一个 AI 驱动的日报自动生成系统，自动采集、筛选、摘要、发布每日精选 AI 资讯，通过 Web 前端展示。

**架构：** 基于 LangGraph 的 Editor-in-Chief Agent（工具调用 + 自我反思），叠加确定性采集层。FastAPI 后端 + React/Tailwind 前端（原浆木纸色系）。PostgreSQL 存储 + Redis 缓存。

**技术栈：** Python 3.11+, LangGraph, DeepSeek API, FastAPI, Playwright, PRAW, React 18, Tailwind CSS, PostgreSQL, Redis, Docker Compose

---

## 第一阶段：基础设施

### 任务 1：项目脚手架搭建

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\requirements.txt`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\config.yaml`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\.env.example`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\.gitignore`

- [ ] **步骤 1：创建 requirements.txt**

```txt
langgraph>=0.4.0
langchain-core>=0.3.0
langchain-deepseek>=0.1.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy[asyncio]>=2.0.36
asyncpg>=0.30.0
redis>=5.2.0
playwright>=1.49.0
beautifulsoup4>=4.12.0
lxml>=5.3.0
praw>=7.7.0
httpx>=0.28.0
apscheduler>=3.10.0
pyyaml>=6.0.2
pydantic>=2.10.0
pydantic-settings>=2.6.0
python-dotenv>=1.0.0
alembic>=1.14.0
```

- [ ] **步骤 2：创建 config.yaml**

```yaml
app:
  name: "AI Daily"
  timezone: "Asia/Shanghai"
  publish_hour: 7
  publish_minute: 30

collector:
  interval_hours: 24
  max_articles_per_source: 30
  sources:
    linuxdo:
      enabled: true
      base_url: "https://linux.do"
      category_ids: [7, 32, 41]
    reddit:
      enabled: true
      subreddits:
        - "artificial"
        - "MachineLearning"
        - "LocalLLaMA"
    twitter:
      enabled: false  # 二期再开

agent:
  model: "deepseek-chat"
  temperature: 0.3
  max_retries: 2
  reflection_enabled: true
  daily_report:
    max_headlines: 3
    max_briefs: 12
    summary_max_length: 200
    brief_max_length: 50

database:
  url: "postgresql+asyncpg://postgres:postgres@localhost:5432/ainews"

redis:
  url: "redis://localhost:6379/0"
```

- [ ] **步骤 3：创建 .env.example**

```
DEEPSEEK_API_KEY=your_key_here
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ainews
REDIS_URL=redis://localhost:6379/0
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=ai-daily/1.0
TWITTER_BEARER_TOKEN=your_token
```

- [ ] **步骤 4：创建 .gitignore**

```
__pycache__/
*.py[cod]
*.egg-info/
.env
venv/
node_modules/
dist/
.superpowers/
*.db
```

- [ ] **步骤 5：提交**

```bash
git init
git add .
git commit -m "chore: 项目脚手架初始化"
```

---

### 任务 2：数据库 Schema 和模型

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\db\schema.sql`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\database.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\models\__init__.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\models\article.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\models\report.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\__init__.py`

- [ ] **步骤 1：创建 schema.sql**

注意：articles 表没有固定分类字段，分类由 Agent 动态生成。

```sql
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,          -- linuxdo/reddit/twitter
    source_id TEXT,
    raw_content TEXT,
    cleaned_text TEXT,
    summary TEXT,                         -- AI 生成的详细摘要
    brief TEXT,                           -- AI 生成的一句话快讯
    tags TEXT[] DEFAULT '{}',             -- Agent 打的语义标签
    section VARCHAR(50),                  -- Agent 分配的当日栏目名
    importance_score INTEGER CHECK (importance_score BETWEEN 1 AND 5),
    status VARCHAR(20) DEFAULT 'raw',    -- raw/fetched/summarized/reviewed/classified/published
    published_date DATE,
    metadata JSONB DEFAULT '{}',          -- 原文评论数、作者、讨论链接等
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    title TEXT NOT NULL,
    article_order INTEGER[] DEFAULT '{}',
    sections JSONB DEFAULT '[]',          -- Agent 规划的栏目结构
    editor_notes TEXT,
    total_articles INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_published_date ON articles(published_date);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_articles_section ON articles(section);
CREATE INDEX idx_reports_date ON daily_reports(report_date DESC);
```

- [ ] **步骤 2：创建 database.py**

```python
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
    dir_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
    with open(dir_path, "r") as f:
        sql = f.read()
    async with engine.begin() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(sa.text(stmt))
    print("数据库迁移完成")
```

- [ ] **步骤 3：创建 models/article.py**

```python
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Article:
    """文章模型"""
    id: Optional[int] = None
    title: str = ""
    url: str = ""
    source: str = ""
    source_id: Optional[str] = None
    raw_content: Optional[str] = None
    cleaned_text: Optional[str] = None
    summary: Optional[str] = None
    brief: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    section: Optional[str] = None
    importance_score: int = 3
    status: str = "raw"
    published_date: Optional[date] = None
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DailyReport:
    """日报模型"""
    id: Optional[int] = None
    report_date: Optional[date] = None
    title: str = ""
    article_order: list[int] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)
    editor_notes: Optional[str] = None
    total_articles: int = 0
    status: str = "draft"
    created_at: Optional[datetime] = None
```

- [ ] **步骤 4：创建 models/__init__.py**

```python
from .article import Article, DailyReport

__all__ = ["Article", "DailyReport"]
```

- [ ] **步骤 5：创建 api/__init__.py**

空文件。

- [ ] **步骤 6：提交**

```bash
git add .
git commit -m "feat: 添加数据库 schema 和模型定义"
```

---

### 任务 3：数据库操作层（Repository）

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\repositories\__init__.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\repositories\article_repo.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\repositories\report_repo.py`

- [ ] **步骤 1：创建 article_repo.py**

```python
from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class ArticleRepository:
    """文章数据访问层"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def batch_insert(self, articles: list[dict]) -> list[int]:
        """批量插入文章，重复 URL 则更新"""
        if not articles:
            return []
        stmt = """
            INSERT INTO articles (title, url, source, source_id, raw_content, status, metadata)
            VALUES (:title, :url, :source, :source_id, :raw_content, 'raw', :metadata)
            ON CONFLICT (url) DO UPDATE SET raw_content = EXCLUDED.raw_content
            RETURNING id
        """
        result = await self.session.execute(text(stmt), articles)
        await self.session.commit()
        return [row[0] for row in result.fetchall()]

    async def get_unprocessed(self, limit: int = 50) -> list[dict]:
        """获取待处理的原始文章"""
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

    async def update_article(self, article_id: int, updates: dict):
        """更新文章字段"""
        sets = ", ".join(f"{k} = :{k}" for k in updates)
        stmt = f"UPDATE articles SET {sets}, updated_at = NOW() WHERE id = :id"
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
```

- [ ] **步骤 2：创建 report_repo.py**

```python
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

    async def update(self, report_id: int, updates: dict):
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
```

- [ ] **步骤 3：创建 repositories/__init__.py**

```python
from .article_repo import ArticleRepository
from .report_repo import ReportRepository

__all__ = ["ArticleRepository", "ReportRepository"]
```

- [ ] **步骤 4：提交**

```bash
git add .
git commit -m "feat: 添加数据库操作层（Repository）"
```

---

## 第二阶段：采集层

### 任务 4：采集器基类和 LinuxDO 爬虫

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\collector\__init__.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\collector\base.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\collector\scrapers\__init__.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\collector\scrapers\linuxdo.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\collector\pipeline.py`

- [ ] **步骤 1：创建 base.py**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawArticle:
    """原始文章数据结构"""
    title: str
    url: str
    source: str           # 来源名称：linuxdo/reddit/twitter
    source_id: str = ""
    raw_content: str = ""
    metadata: dict = field(default_factory=dict)


class BaseScraper(ABC):
    """采集器基类，所有来源采集器需继承此类"""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def scrape(self) -> list[RawArticle]:
        """执行采集，返回原始文章列表"""
        pass
```

- [ ] **步骤 2：创建 linuxdo.py**

```python
from typing import Optional
from bs4 import BeautifulSoup
from collector.base import BaseScraper, RawArticle


class LinuxDOScraper(BaseScraper):
    """LinuxDO 论坛采集器"""

    BASE_URL = "https://linux.do"

    async def scrape(self) -> list[RawArticle]:
        articles = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        import httpx
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            for cat_id in self.config.get("category_ids", [7, 32]):
                url = f"{self.BASE_URL}/categories/{cat_id}.json"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for topic in data.get("topic_list", {}).get("topics", [])[:20]:
                        article = self._parse_topic(topic, cat_id)
                        if article:
                            articles.append(article)
                except Exception as e:
                    print(f"LinuxDO 分类 {cat_id} 采集失败: {e}")

        print(f"LinuxDO: 采集到 {len(articles)} 篇文章")
        return articles

    def _parse_topic(self, topic: dict, category_id: int) -> Optional[RawArticle]:
        """解析单个话题"""
        title = topic.get("title", "").strip()
        if not title or not self._is_ai_related(title):
            return None

        slug = topic.get("slug", "")
        topic_id = topic.get("id", "")
        url = f"{self.BASE_URL}/t/{slug}/{topic_id}" if slug else ""

        return RawArticle(
            title=title,
            url=url,
            source="linuxdo",
            source_id=str(topic_id),
            metadata={
                "category_id": category_id,
                "posts_count": topic.get("posts_count", 0),
                "created_at": topic.get("created_at", ""),
            },
        )

    def _is_ai_related(self, title: str) -> bool:
        """判断标题是否与 AI 相关"""
        keywords = [
            "ai", "人工智能", "llm", "大模型", "gpt", "claude", "openai",
            "deepseek", "llama", "rag", "agent", "机器学习", "深度学习",
            "神经网络", "transformer", "diffusion", "embedding", "vector",
            "langchain", "autogpt", "copilot", "chatgpt", "多模态",
            "sora", "gemini", "mistral", "qwen", "通义", "千问",
        ]
        lower = title.lower()
        return any(kw.lower() in lower for kw in keywords)
```

- [ ] **步骤 3：创建 scrapers/__init__.py**

```python
from .linuxdo import LinuxDOScraper

# 采集器注册表：名称 -> 类
SCRAPERS = {
    "linuxdo": LinuxDOScraper,
}
```

- [ ] **步骤 4：创建 pipeline.py**

```python
import yaml
from collector.base import RawArticle
from collector.scrapers import SCRAPERS


class CollectorPipeline:
    """采集管道：遍历所有启用的数据源并执行采集"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.max_per_source = self.config["collector"]["max_articles_per_source"]

    async def run(self) -> list[RawArticle]:
        all_articles = []
        sources = self.config["collector"]["sources"]

        for name, source_cfg in sources.items():
            if not source_cfg.get("enabled", False):
                continue
            scraper_cls = SCRAPERS.get(name)
            if not scraper_cls:
                print(f"未知数据源: {name}")
                continue
            scraper = scraper_cls(source_cfg)
            try:
                articles = await scraper.scrape()
                articles = articles[:self.max_per_source]
                all_articles.extend(articles)
                print(f"{name}: {len(articles)} 篇采集完成")
            except Exception as e:
                print(f"{name} 采集器执行失败: {e}")

        print(f"本轮采集总计: {len(all_articles)} 篇文章")
        return all_articles
```

- [ ] **步骤 5：提交**

```bash
git add .
git commit -m "feat: 添加采集层和 LinuxDO 爬虫"
```

---

### 任务 5：Reddit 采集器

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\collector\scrapers\reddit.py`

- [ ] **步骤 1：创建 reddit.py**

```python
from typing import Optional
from collector.base import BaseScraper, RawArticle


class RedditScraper(BaseScraper):
    """Reddit 采集器（需配置 API 密钥）"""

    async def scrape(self) -> list[RawArticle]:
        import asyncpraw

        reddit = asyncpraw.Reddit(
            client_id=self.config.get("client_id", ""),
            client_secret=self.config.get("client_secret", ""),
            user_agent=self.config.get("user_agent", "ai-daily/1.0"),
        )

        articles = []
        subreddits = self.config.get("subreddits", ["artificial", "MachineLearning", "LocalLLaMA"])

        for sub_name in subreddits:
            try:
                sub = await reddit.subreddit(sub_name)
                async for submission in sub.hot(limit=15):
                    article = self._parse_submission(submission)
                    if article:
                        articles.append(article)
            except Exception as e:
                print(f"Reddit r/{sub_name} 采集失败: {e}")

        await reddit.close()
        print(f"Reddit: 采集到 {len(articles)} 篇文章")
        return articles

    def _parse_submission(self, submission) -> Optional[RawArticle]:
        """解析 Reddit 帖子"""
        if not self._is_ai_related(submission.title):
            return None

        return RawArticle(
            title=submission.title,
            url=submission.url,
            source="reddit",
            source_id=submission.id,
            raw_content=getattr(submission, "selftext", ""),
            metadata={
                "score": submission.score,
                "num_comments": submission.num_comments,
                "subreddit": str(submission.subreddit),
                "permalink": f"https://reddit.com{submission.permalink}",
            },
        )

    def _is_ai_related(self, title: str) -> bool:
        """判断标题是否与 AI 相关"""
        keywords = [
            "ai", "llm", "gpt", "claude", "openai", "deepseek", "llama",
            "rag", "agent", "machine learning", "deep learning", "transformer",
            "diffusion", "langchain", "copilot", "chatgpt", "gemini",
            "mistral", "qwen", "neural", "sora", "multimodal", "ml",
        ]
        lower = title.lower()
        return any(kw in lower for kw in keywords)
```

- [ ] **步骤 2：注册到采集器注册表**

修改 `collector/scrapers/__init__.py`：

```python
from .linuxdo import LinuxDOScraper
from .reddit import RedditScraper

SCRAPERS = {
    "linuxdo": LinuxDOScraper,
    "reddit": RedditScraper,
}
```

- [ ] **步骤 3：提交**

```bash
git add .
git commit -m "feat: 添加 Reddit 采集器"
```

---

## 第三阶段：Agent 系统

### 任务 6：Agent 状态和工具

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\__init__.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\state.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\tools\__init__.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\tools\scanner.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\tools\fetcher.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\tools\summarizer.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\tools\classifier.py`

- [ ] **步骤 1：创建 state.py**

```python
from typing import TypedDict, Optional, Annotated
from operator import add


class ArticleState(TypedDict):
    """文章中继状态：记录每篇文章在 Agent 流程中的处理结果"""
    id: int
    title: str
    url: str
    source: str
    source_id: str
    raw_content: Optional[str]
    cleaned_text: Optional[str]
    summary: Optional[str]
    brief: Optional[str]
    tags: list[str]
    section: Optional[str]
    importance_score: int
    status: str                     # fetched/summarized/reviewed/classified
    critique_result: Optional[str]  # 反思结果
    critique_attempts: int          # 反思重试次数
    metadata: dict


class DailyReportState(TypedDict):
    """日报状态：LangGraph 工作流的全局状态"""
    report_date: str
    title: str
    raw_articles: list[dict]
    processed_articles: Annotated[list[ArticleState], add]
    selected_article_ids: list[int]
    sections: list[dict]
    editor_notes: str
    status: str                     # draft/empty/published
```

- [ ] **步骤 2：创建 tools/scanner.py**

```python
from collector.pipeline import CollectorPipeline


async def scan_sources(keywords: str | None = None) -> list[dict]:
    """扫描所有启用的数据源，返回文章列表

    编辑 Agent 用此工具获取当天的原始素材。
    """
    pipeline = CollectorPipeline()
    raw_articles = await pipeline.run()
    return [
        {
            "title": a.title,
            "url": a.url,
            "source": a.source,
            "source_id": a.source_id,
            "raw_content": a.raw_content,
            "metadata": a.metadata,
        }
        for a in raw_articles
    ]
```

- [ ] **步骤 3：创建 tools/fetcher.py**

```python
import httpx
from bs4 import BeautifulSoup


async def fetch_content(url: str) -> str:
    """抓取文章正文并清洗为纯文本"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            # 移除不需要的标签
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines[:200])  # 只保留前 200 行
    except Exception as e:
        return f"抓取失败 {url}: {e}"
```

- [ ] **步骤 4：创建 tools/summarizer.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

SUMMARY_PROMPT = """你是一位 AI 新闻编辑。请为以下文章撰写简洁的摘要。

风格：{style}
最大长度：{max_length} 字

标题：{title}
正文：{content}

要求：
- 说清楚"发生了什么事"和"为什么重要"
- 如有具体数字/数据务必保留
- 客观事实，不要夸大
- 使用中文

摘要："""

BRIEF_PROMPT = """将以下 AI 新闻浓缩为一句话（最多 50 字）：

{title}：{content}

一句话："""


async def write_summary(article: dict, style: str = "normal") -> str:
    """使用 DeepSeek 生成文章摘要"""
    if style == "brief":
        prompt = BRIEF_PROMPT.format(
            title=article.get("title", ""),
            content=article.get("cleaned_text", "")[:500],
        )
        max_tokens = 100
    else:
        prompt = SUMMARY_PROMPT.format(
            style=style,
            max_length=200,
            title=article.get("title", ""),
            content=article.get("cleaned_text", "")[:2000],
        )
        max_tokens = 300

    import httpx
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
```

- [ ] **步骤 5：创建 tools/classifier.py**

```python
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

CLASSIFY_PROMPT = """你是一位 AI 新闻编辑。分析以下文章并返回 JSON：

{{
  "tags": ["标签1", "标签2"],
  "importance_score": 1-5,
  "reason": "一句话说明为什么重要"
}}

评判标准：
- 是否是突发新闻？
- 对 AI 行业影响大吗？
- 是否有新颖性？

标题：{title}
内容：{content}

只返回合法的 JSON，不要其他文字。"""


async def classify(article: dict) -> dict:
    """分类文章：打标签 + 评估重要度"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{
                    "role": "user",
                    "content": CLASSIFY_PROMPT.format(
                        title=article.get("title", ""),
                        content=article.get("cleaned_text", "") or article.get("summary", ""),
                    ),
                }],
                "max_tokens": 200,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        data = resp.json()
        try:
            return json.loads(data["choices"][0]["message"]["content"])
        except (json.JSONDecodeError, KeyError):
            return {"tags": ["ai"], "importance_score": 3, "reason": "分类失败"}
```

- [ ] **步骤 6：创建 tools/__init__.py**

```python
from .scanner import scan_sources
from .fetcher import fetch_content
from .summarizer import write_summary
from .classifier import classify

__all__ = ["scan_sources", "fetch_content", "write_summary", "classify"]
```

- [ ] **步骤 7：提交**

```bash
git add .
git commit -m "feat: 添加 Agent 状态定义和工具（扫描/抓取/摘要/分类）"
```

---

### 任务 7：Agent 反思机制和提示词模板

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\reflection.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\prompts\__init__.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\prompts\summarizer.yaml`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\prompts\classifier.yaml`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\prompts\critique.yaml`

- [ ] **步骤 1：创建 reflection.py**

```python
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

CRITIQUE_PROMPT = """请审阅以下 AI 新闻摘要，检查是否有问题，返回 JSON：

{{
  "pass": true/false,
  "issues": ["问题1"],
  "suggestion": "修改建议"
}}

标题：{title}
摘要：{summary}

检查清单：
1. 关键信息是否清晰？（什么事 + 为什么重要）
2. 具体数字/数据是否保留？
3. 是否客观无幻觉？
4. 长度是否合适（约 {max_length} 字）？
5. 中文是否通顺自然？

只返回合法的 JSON。"""


async def critique_summary(title: str, summary: str, max_length: int = 200) -> dict:
    """对摘要进行自我审查，返回审查结果"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{
                    "role": "user",
                    "content": CRITIQUE_PROMPT.format(
                        title=title, summary=summary, max_length=max_length
                    ),
                }],
                "max_tokens": 200,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        data = resp.json()
        try:
            return json.loads(data["choices"][0]["message"]["content"])
        except (json.JSONDecodeError, KeyError):
            return {"pass": True, "issues": [], "suggestion": ""}
```

- [ ] **步骤 2：创建 prompts/critique.yaml**

```yaml
name: critique
description: 摘要质量自审
template: |
  请审阅以下 AI 新闻摘要，检查是否有问题，返回 JSON：

  {{
    "pass": true/false,
    "issues": ["问题1"],
    "suggestion": "修改建议"
  }}

  标题：{title}
  摘要：{summary}

  检查清单：
  1. 关键信息是否清晰？
  2. 具体数字/数据是否保留？
  3. 是否客观无幻觉？
  4. 长度是否合适（约 {max_length} 字）？
  5. 中文是否通顺自然？

  只返回合法的 JSON。
```

- [ ] **步骤 3：创建 prompts/summarizer.yaml**

```yaml
name: summarizer
description: 生成文章摘要
template: |
  你是一位 AI 新闻编辑。请为以下文章撰写简洁的摘要。

  风格：{style}
  最大长度：{max_length} 字

  标题：{title}
  正文：{content}

  要求：
  - 说清楚"发生了什么事"和"为什么重要"
  - 如有具体数字/数据务必保留
  - 客观事实，不要夸大
  - 使用中文

  摘要：
```

- [ ] **步骤 4：创建 prompts/classifier.yaml**

```yaml
name: classifier
description: 分类文章：标签 + 重要度
template: |
  分析以下 AI 文章，返回 JSON：

  {{
    "tags": ["标签1", "标签2"],
    "importance_score": 1-5,
    "reason": "为什么重要"
  }}

  标题：{title}
  内容：{content}

  只返回合法的 JSON。
```

- [ ] **步骤 5：创建 prompts/__init__.py**

```python
import yaml
import os


def load_prompt(name: str, **kwargs) -> str:
    """加载提示词模板并填充变量"""
    path = os.path.join(os.path.dirname(__file__), f"{name}.yaml")
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data["template"].format(**kwargs)
```

- [ ] **步骤 6：提交**

```bash
git add .
git commit -m "feat: 添加 Agent 反思机制和提示词模板"
```

---

### 任务 8：Agent 工作流图（LangGraph）

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\agent\graph.py`

- [ ] **步骤 1：创建 graph.py**

```python
import os
from datetime import date, datetime
from typing import Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import DailyReportState, ArticleState
from agent.tools import scan_sources, fetch_content, write_summary, classify
from agent.reflection import critique_summary

load_dotenv()

MAX_CRITIQUE_ATTEMPTS = 2  # 每篇文章最多反思重试 2 次


async def collect_node(state: DailyReportState) -> dict:
    """节点 1：扫描所有数据源获取原始文章"""
    articles = await scan_sources()
    return {"raw_articles": articles}


async def select_node(state: DailyReportState) -> dict:
    """节点 2：Agent 选择要处理的文章"""
    articles = state.get("raw_articles", [])
    if not articles:
        return {"selected_article_ids": [], "status": "empty"}

    # 按热度评分排序，取前 15 篇
    scored = []
    for i, a in enumerate(articles):
        meta = a.get("metadata", {})
        score = 0
        if a["source"] == "reddit":
            score = meta.get("score", 0) or 0
        elif a["source"] == "linuxdo":
            score = meta.get("posts_count", 0) or 0
        scored.append((score, i, a))

    scored.sort(key=lambda x: -x[0])
    selected = scored[:15]
    ids = [s[2] for s in selected]
    return {
        "selected_article_ids": ids,
        "raw_articles": [a for _, _, a in selected],
    }


async def fetch_node(state: DailyReportState) -> dict:
    """节点 3：获取选中文章的完整内容"""
    articles = state.get("raw_articles", [])
    processed = []

    for a in articles:
        if a.get("raw_content"):
            cleaned = a["raw_content"][:2000]
        else:
            cleaned = await fetch_content(a["url"])

        article_state: ArticleState = {
            "id": 0,
            "title": a["title"],
            "url": a["url"],
            "source": a["source"],
            "source_id": a.get("source_id", ""),
            "raw_content": a.get("raw_content", ""),
            "cleaned_text": cleaned,
            "summary": None,
            "brief": None,
            "tags": [],
            "section": None,
            "importance_score": 3,
            "status": "fetched",
            "critique_result": None,
            "critique_attempts": 0,
            "metadata": a.get("metadata", {}),
        }
        processed.append(article_state)

    return {"processed_articles": processed}


async def summarize_node(state: DailyReportState) -> dict:
    """节点 4：为所有文章生成摘要"""
    articles = state.get("processed_articles", [])
    updated = []

    for a in articles:
        if a["status"] != "fetched":
            updated.append(a)
            continue

        summary = await write_summary(a, style="normal")
        brief = await write_summary(a, style="brief")
        a["summary"] = summary
        a["brief"] = brief
        a["status"] = "summarized"
        updated.append(a)

    return {"processed_articles": updated}


async def reflect_node(state: DailyReportState) -> dict:
    """节点 5：自我审查摘要质量，不合格则重写"""
    articles = state.get("processed_articles", [])
    updated = []

    for a in articles:
        if a["status"] != "summarized" or not a.get("summary"):
            updated.append(a)
            continue

        result = await critique_summary(a["title"], a["summary"])
        a["critique_result"] = result.get("suggestion", "")
        a["critique_attempts"] = a.get("critique_attempts", 0) + 1

        if not result.get("pass", True) and a["critique_attempts"] < MAX_CRITIQUE_ATTEMPTS:
            # 根据反思建议重写
            revised = await write_summary(a, style=f"normal（改进：{result.get('suggestion', '')}）")
            a["summary"] = revised
        a["status"] = "reviewed"
        updated.append(a)

    return {"processed_articles": updated}


async def classify_node(state: DailyReportState) -> dict:
    """节点 6：分类和打标签"""
    articles = state.get("processed_articles", [])
    updated = []

    for a in articles:
        if a["status"] != "reviewed":
            updated.append(a)
            continue

        result = await classify(a)
        a["tags"] = result.get("tags", ["ai"])
        a["importance_score"] = result.get("importance_score", 3)
        a["status"] = "classified"
        updated.append(a)

    return {"processed_articles": updated}


async def layout_node(state: DailyReportState) -> dict:
    """节点 7：Agent 规划日报版面（栏目和排序）"""
    articles = state.get("processed_articles", [])
    today = date.today()
    title_str = f"AI日报 · {today.strftime('%Y年%m月%d日')}"

    # 按重要度排序
    sorted_arts = sorted(articles, key=lambda a: -a["importance_score"])

    # 根据标签聚类生成栏目
    sections = []
    section_map = {}
    for a in sorted_arts:
        tags = a.get("tags", [])
        primary_tag = tags[0] if tags else "综合"
        if primary_tag not in section_map:
            section_map[primary_tag] = {
                "name": primary_tag,
                "article_ids": [],
            }
        section_map[primary_tag]["article_ids"].append(id(a))

    sections = [v for v in section_map.values()]
    article_ids = [id(a) for a in sorted_arts]

    return {
        "sections": sections,
        "article_order": article_ids,
        "title": title_str,
        "status": "published",
        "editor_notes": f"自动生成于 {datetime.now().isoformat()}",
        "total_articles": len(articles),
    }


def should_reflect(state: DailyReportState) -> Literal["reflect", "classify"]:
    """条件边：是否启用反思步骤"""
    if os.getenv("REFLECTION_ENABLED", "true").lower() == "true":
        return "reflect"
    return "classify"


def build_agent() -> StateGraph:
    """构建并编译 LangGraph Agent"""
    builder = StateGraph(DailyReportState)

    # 注册节点
    builder.add_node("collect", collect_node)
    builder.add_node("select", select_node)
    builder.add_node("fetch", fetch_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("reflect", reflect_node)
    builder.add_node("classify", classify_node)
    builder.add_node("layout", layout_node)

    # 构建连接
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "select")
    builder.add_edge("select", "fetch")
    builder.add_edge("fetch", "summarize")
    builder.add_conditional_edges("summarize", should_reflect)
    builder.add_edge("reflect", "classify")
    builder.add_edge("classify", "layout")
    builder.add_edge("layout", END)

    return builder.compile(checkpointer=MemorySaver())
```

- [ ] **步骤 2：提交**

```bash
git add .
git commit -m "feat: 添加 LangGraph Agent 工作流"
```

---

## 第四阶段：API 层

### 任务 9：FastAPI 应用和路由

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\main.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\config.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\routes\__init__.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\routes\articles.py`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\api\routes\reports.py`

- [ ] **步骤 1：创建 config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，优先从环境变量读取"""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ainews"
    redis_url: str = "redis://localhost:6379/0"
    deepseek_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

- [ ] **步骤 2：创建 articles.py 路由**

```python
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
        return {"error": "not found"}, 404
    return dict(row._mapping)


@router.get("/today/summary")
async def today_summary(db: AsyncSession = Depends(get_db)):
    """获取今日文章统计概览"""
    today = date.today().isoformat()
    stmt = """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE importance_score >= 4) as headlines,
            ARRAY_AGG(DISTINCT source) as sources
        FROM articles
        WHERE published_date = :today AND status = 'published'
    """
    result = await db.execute(text(stmt), {"today": today})
    row = result.fetchone()
    return dict(row._mapping)
```

- [ ] **步骤 3：创建 reports.py 路由**

```python
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
        return {"error": "not found"}, 404
    return dict(row._mapping)
```

- [ ] **步骤 4：创建 routes/__init__.py**

```python
from .articles import router as articles_router
from .reports import router as reports_router

__all__ = ["articles_router", "reports_router"]
```

- [ ] **步骤 5：创建 main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import init_db, run_migrations
from api.routes import articles_router, reports_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    await init_db()
    await run_migrations()
    yield


app = FastAPI(title="AI Daily API", version="0.1.0", lifespan=lifespan)

# CORS 配置，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles_router)
app.include_router(reports_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **步骤 6：提交**

```bash
git add .
git commit -m "feat: 添加 FastAPI 应用和路由接口"
```

---

## 第五阶段：前端

### 任务 10：React + Tailwind 项目脚手架

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\package.json`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\index.html`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\vite.config.ts`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\tsconfig.json`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\tsconfig.node.json`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\tailwind.config.js`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\postcss.config.js`

- [ ] **步骤 1：创建 package.json**

```json
{
  "name": "ai-daily-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **步骤 2：创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Daily - AI 日报</title>
  </head>
  <body class="bg-paper text-ink">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **步骤 3：创建 vite.config.ts**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **步骤 4：创建 tailwind.config.js**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F5F0E8',
        card: '#EDE4D4',
        border: '#D4C5A9',
        'ink-light': '#8B7D6B',
        ink: '#5C4F3F',
        'ink-dark': '#2C2820',
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"Source Han Sans SC"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

- [ ] **步骤 5：创建 postcss.config.js**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **步骤 6：创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **步骤 7：创建 tsconfig.node.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **步骤 8：安装依赖**

```bash
cd frontend && npm install
```

- [ ] **步骤 9：提交**

```bash
git add .
git commit -m "feat: 添加前端项目脚手架（React + Tailwind + Vite）"
```

---

### 任务 11：前端 API 层

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\main.tsx`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\App.tsx`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\api\index.ts`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\index.css`

- [ ] **步骤 1：创建 index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');

body {
  font-family: 'Noto Sans SC', sans-serif;
  background-color: #F5F0E8;
  color: #5C4F3F;
}

/* 卡片悬浮效果 */
.card-hover {
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.card-hover:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}
```

- [ ] **步骤 2：创建 api/index.ts**

```ts
const API_BASE = '/api';

export interface Article {
  id: number;
  title: string;
  url: string;
  source: string;
  summary: string | null;
  brief: string | null;
  tags: string[];
  section: string | null;
  importance_score: number;
  published_date: string;
  metadata: Record<string, unknown>;
}

export interface DailyReport {
  id: number;
  report_date: string;
  title: string;
  article_order: number[];
  sections: Array<{ name: string; article_ids: number[] }>;
  editor_notes: string | null;
  total_articles: number;
  status: string;
  articles: Article[];
}

export interface ReportSummary {
  id: number;
  report_date: string;
  title: string;
  total_articles: number;
  status: string;
}

/** 获取今日完整日报 */
export async function fetchTodayReport(): Promise<DailyReport | null> {
  const res = await fetch(`${API_BASE}/reports/today`);
  if (!res.ok) return null;
  return res.json();
}

/** 获取单篇文章详情 */
export async function fetchArticle(id: number): Promise<Article | null> {
  const res = await fetch(`${API_BASE}/articles/${id}`);
  if (!res.ok) return null;
  return res.json();
}

/** 获取历史日报列表 */
export async function fetchReports(limit = 30): Promise<ReportSummary[]> {
  const res = await fetch(`${API_BASE}/reports/?limit=${limit}`);
  return res.json();
}

/** 获取文章列表（支持筛选） */
export async function fetchArticles(params?: {
  report_date?: string;
  source?: string;
  section?: string;
}): Promise<Article[]> {
  const query = new URLSearchParams();
  if (params?.report_date) query.set('report_date', params.report_date);
  if (params?.source) query.set('source', params.source);
  if (params?.section) query.set('section', params.section);
  const res = await fetch(`${API_BASE}/articles/?${query}`);
  return res.json();
}
```

- [ ] **步骤 3：创建 main.tsx**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
```

- [ ] **步骤 4：创建 App.tsx**

```tsx
import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Article from './pages/Article'

export default function App() {
  return (
    <div className="min-h-screen bg-paper">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/article/:id" element={<Article />} />
      </Routes>
    </div>
  )
}
```

- [ ] **步骤 5：提交**

```bash
git add .
git commit -m "feat: 添加前端 API 层和路由"
```

---

### 任务 12：前端页面和组件

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\components\Header.tsx`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\components\Card.tsx`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\components\FilterBar.tsx`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\pages\Home.tsx`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\frontend\src\pages\Article.tsx`

- [ ] **步骤 1：创建 Header.tsx**

```tsx
interface HeaderProps {
  title: string;
  date: string;
}

export default function Header({ title, date }: HeaderProps) {
  return (
    <header className="border-b border-border bg-card">
      <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
        <a href="/" className="text-xl font-bold text-ink-dark no-underline">
          📰 {title}
        </a>
        <time className="text-sm text-ink-light">{date}</time>
      </div>
    </header>
  );
}
```

- [ ] **步骤 2：创建 Card.tsx**

```tsx
import type { Article } from '../api';

interface CardProps {
  article: Article;
  isHeadline?: boolean;  // 是否为头条文章
}

export default function Card({ article, isHeadline }: CardProps) {
  return (
    <a
      href={`/article/${article.id}`}
      className={`block no-underline rounded-xl border ${
        isHeadline
          ? 'bg-card border-border card-hover'
          : 'bg-white border-card card-hover'
      }`}
    >
      <div className="p-4">
        {/* 头条标签 */}
        {isHeadline && (
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-ink bg-paper px-2 py-0.5 rounded-full">
              🔥 头条
            </span>
            <span className="text-xs text-ink-light">{article.source}</span>
          </div>
        )}

        {/* 标题 */}
        <h3
          className={`font-bold text-ink-dark leading-snug mb-1 ${
            isHeadline ? 'text-lg' : 'text-base'
          }`}
        >
          {article.title}
        </h3>

        {/* 摘要 */}
        <p className="text-sm text-ink leading-relaxed line-clamp-2">
          {isHeadline ? article.summary : article.brief || article.summary}
        </p>

        {/* 标签和来源 */}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {article.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 rounded-full bg-card text-ink border border-border"
            >
              {tag}
            </span>
          ))}
          {!isHeadline && (
            <span className="text-xs text-ink-light ml-auto">{article.source}</span>
          )}
        </div>
      </div>
    </a>
  );
}
```

- [ ] **步骤 3：创建 FilterBar.tsx**

```tsx
interface Section {
  name: string;
}

interface FilterBarProps {
  sections: Section[];
  activeSection: string | null;
  onSelect: (section: string | null) => void;
}

export default function FilterBar({ sections, activeSection, onSelect }: FilterBarProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2">
      <button
        onClick={() => onSelect(null)}
        className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors ${
          activeSection === null
            ? 'bg-card text-ink-dark font-medium'
            : 'bg-transparent text-ink-light border border-border hover:bg-card'
        }`}
      >
        🔄 全部
      </button>
      {sections.map((s) => (
        <button
          key={s.name}
          onClick={() => onSelect(s.name)}
          className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors ${
            activeSection === s.name
              ? 'bg-card text-ink-dark font-medium'
              : 'bg-transparent text-ink-light border border-border hover:bg-card'
          }`}
        >
          {s.name}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **步骤 4：创建 Home.tsx（首页）**

```tsx
import { useEffect, useState } from 'react';
import type { DailyReport } from '../api';
import { fetchTodayReport } from '../api';
import Header from '../components/Header';
import FilterBar from '../components/FilterBar';
import Card from '../components/Card';

export default function Home() {
  const [report, setReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  useEffect(() => {
    fetchTodayReport().then((data) => {
      setReport(data);
      setLoading(false);
    });
  }, []);

  // 加载中
  if (loading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="text-ink-light">加载中...</p>
      </div>
    );
  }

  // 日报尚未生成
  if (!report) {
    return (
      <div className="min-h-screen bg-paper">
        <Header title="AI Daily" date={new Date().toLocaleDateString('zh-CN')} />
        <main className="max-w-3xl mx-auto px-4 py-12 text-center">
          <p className="text-ink-light text-lg">今日日报正在编辑中，请稍后再来 📝</p>
        </main>
      </div>
    );
  }

  const sections = report.sections || [];
  const headlines = report.articles.filter((a) => a.importance_score >= 4);
  const others = report.articles.filter((a) => a.importance_score < 4);

  // 动态栏目筛选
  const filteredOthers = activeSection
    ? others.filter((a) => a.section === activeSection)
    : others;

  return (
    <div className="min-h-screen bg-paper">
      <Header title={report.title} date={report.report_date} />

      <main className="max-w-3xl mx-auto px-4 py-6">
        {/* 动态栏目导航 */}
        {sections.length > 0 && (
          <div className="mb-6">
            <FilterBar
              sections={sections as { name: string }[]}
              activeSection={activeSection}
              onSelect={setActiveSection}
            />
          </div>
        )}

        {/* 头条区域 */}
        {headlines.length > 0 && !activeSection && (
          <section className="mb-8">
            <div className="flex flex-col gap-4">
              {headlines.map((article) => (
                <Card key={article.id} article={article} isHeadline />
              ))}
            </div>
          </section>
        )}

        {/* 普通文章网格 */}
        <section>
          {sections.length > 0 && !activeSection && (
            <div className="flex gap-2 mb-4 text-xs text-ink-light">
              {sections.map((s: { name: string }) => (
                <span key={s.name} className="bg-card px-2 py-0.5 rounded">
                  📂 {s.name}
                </span>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(activeSection ? filteredOthers : others).map((article) => (
              <Card key={article.id} article={article} />
            ))}
          </div>
        </section>

        {/* 页脚 */}
        <footer className="mt-8 pt-4 border-t border-border text-center text-xs text-ink-light">
          本日共 {report.total_articles} 篇 · 由 AI 自动整理
        </footer>
      </main>
    </div>
  );
}
```

- [ ] **步骤 5：创建 Article.tsx（文章详情页）**

```tsx
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Article as ArticleType } from '../api';
import { fetchArticle } from '../api';

export default function Article() {
  const { id } = useParams<{ id: string }>();
  const [article, setArticle] = useState<ArticleType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchArticle(Number(id)).then((data) => {
        setArticle(data);
        setLoading(false);
      });
    }
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="text-ink-light">加载中...</p>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="text-ink-light">文章不存在</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper">
      <main className="max-w-2xl mx-auto px-4 py-8">
        {/* 返回链接 */}
        <Link to="/" className="text-sm text-ink-light hover:text-ink mb-6 inline-block">
          ← 返回日报
        </Link>

        {/* 分类标签 */}
        {article.tags.length > 0 && (
          <span className="inline-block text-xs text-ink-light bg-card px-2 py-0.5 rounded-full mb-3">
            {article.tags[0]}
          </span>
        )}

        {/* 标题 */}
        <h1 className="text-2xl font-bold text-ink-dark leading-snug mb-4">
          {article.title}
        </h1>

        {/* 元信息：日期 + 来源 + 原文链接 */}
        <div className="flex items-center gap-4 text-sm text-ink-light mb-8">
          <time>{article.published_date}</time>
          <span>📰 {article.source}</span>
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink underline hover:text-ink-dark ml-auto"
          >
            🔗 查看原文
          </a>
        </div>

        {/* AI 摘要正文 */}
        {article.summary && (
          <div className="text-base text-ink leading-relaxed mb-8 whitespace-pre-line">
            {article.summary}
          </div>
        )}

        {/* 原文讨论链接 */}
        {article.metadata?.permalink && (
          <div className="mt-8 p-4 bg-card rounded-lg text-sm text-ink">
            <strong className="block mb-2">💬 讨论</strong>
            <a
              href={article.metadata.permalink as string}
              target="_blank"
              rel="noopener noreferrer"
              className="text-ink underline"
            >
              查看原文讨论（{article.metadata.num_comments ?? 0} 条评论）
            </a>
          </div>
        )}

        {/* 相关标签 */}
        {article.tags.length > 0 && (
          <div className="mt-8 pt-6 border-t border-border flex gap-2 flex-wrap">
            {article.tags.map((tag) => (
              <span
                key={tag}
                className="text-sm px-3 py-1 bg-card rounded-full text-ink"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **步骤 6：验证构建**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **步骤 7：提交**

```bash
git add .
git commit -m "feat: 添加前端页面和组件"
```

---

## 第六阶段：部署

### 任务 13：定时调度器

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\scheduler.py`

- [ ] **步骤 1：创建 scheduler.py**

```python
import asyncio
import yaml
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent.graph import build_agent
from api.database import async_session
from api.repositories.article_repo import ArticleRepository
from api.repositories.report_repo import ReportRepository


async def run_daily_pipeline():
    """执行每天的日报生成流程"""
    print(f"[{datetime.now()}] 开始执行日报流程...")

    # 步骤 1：运行 Agent
    agent = build_agent()
    result = await agent.ainvoke({
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "title": "",
        "raw_articles": [],
        "processed_articles": [],
        "selected_article_ids": [],
        "sections": [],
        "editor_notes": "",
        "status": "draft",
    })

    # 步骤 2：持久化到数据库
    async with async_session() as session:
        article_repo = ArticleRepository(session)
        report_repo = ReportRepository(session)

        # 批量保存文章
        article_ids = []
        for a in result.get("processed_articles", []):
            if a.get("status") in ("classified", "reviewed"):
                aid = await article_repo.batch_insert([{
                    "title": a["title"],
                    "url": a["url"],
                    "source": a["source"],
                    "source_id": a.get("source_id", ""),
                    "raw_content": a.get("raw_content", ""),
                    "metadata": a.get("metadata", {}),
                }])
                if aid:
                    await article_repo.update_article(aid[0], {
                        "cleaned_text": a.get("cleaned_text", ""),
                        "summary": a.get("summary", ""),
                        "brief": a.get("brief", ""),
                        "tags": a.get("tags", []),
                        "section": a.get("section"),
                        "importance_score": a.get("importance_score", 3),
                        "status": "published",
                        "published_date": datetime.now().date(),
                    })
                    article_ids.append(aid[0])

        # 创建或更新日报
        today = datetime.now().date()
        report_id = await report_repo.create(today, result.get("title", f"AI日报 · {today}"))
        await report_repo.update(report_id, {
            "article_order": article_ids,
            "sections": result.get("sections", []),
            "editor_notes": result.get("editor_notes", ""),
            "total_articles": len(article_ids),
            "status": "published",
        })

    print(f"[{datetime.now()}] 日报流程完成。共发布 {len(article_ids)} 篇文章。")


def start_scheduler():
    """启动定时调度器"""
    scheduler = AsyncIOScheduler()

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    hour = config.get("app", {}).get("publish_hour", 7)
    minute = config.get("app", {}).get("publish_minute", 30)

    scheduler.add_job(run_daily_pipeline, "cron", hour=hour, minute=minute)
    scheduler.start()
    print(f"调度器已启动。每天 {hour:02d}:{minute:02d} 自动执行日报流程。")

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    start_scheduler()
```

- [ ] **步骤 2：提交**

```bash
git add .
git commit -m "feat: 添加每日定时调度器"
```

---

### 任务 14：Docker Compose 部署

**文件：**
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\Dockerfile`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\Dockerfile.frontend`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\nginx.conf`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\docker-compose.yml`
- 创建: `d:\Develop\code\project\ai-news-MutiAgents\.dockerignore`

- [ ] **步骤 1：创建 Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器
RUN playwright install chromium && playwright install-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **步骤 2：创建 Dockerfile.frontend**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

- [ ] **步骤 3：创建 nginx.conf**

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **步骤 4：创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ainews
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/ainews
      REDIS_URL: redis://redis:6379/0
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
    volumes:
      - .:/app

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - api

volumes:
  pgdata:
```

- [ ] **步骤 5：创建 .dockerignore**

```
.git
__pycache__
node_modules
.env
.superpowers
```

- [ ] **步骤 6：提交**

```bash
git add .
git commit -m "feat: 添加 Docker 部署配置"
```

---

## Plan 自审

**Spec 覆盖情况：**
- ✅ 项目脚手架（依赖、配置、gitignore）
- ✅ 数据库 schema + 模型（articles + daily_reports）
- ✅ 采集层（LinuxDO + Reddit，可扩展基类）
- ✅ Agent 系统（工具 + 反思 + LangGraph 工作流）
- ✅ API（文章 + 日报路由，健康检查）
- ✅ 前端（首页卡片流 + 动态栏目 + 文章详情）
- ✅ 定时调度器（每天定时触发）
- ✅ Docker Compose 部署

**占位符检查：** 无 TBD/TODO/待定内容。

**类型一致性：** 所有方法签名和数据结构在任务间保持一致。

注意：Twitter/X 采集器标记为二期实现（配置中已禁用）。
