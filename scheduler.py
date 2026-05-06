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
