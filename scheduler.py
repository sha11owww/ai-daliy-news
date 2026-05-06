import asyncio
import json
import yaml
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent.graph import build_agent
from api.database import async_session
from api.repositories.article_repo import ArticleRepository
from api.repositories.report_repo import ReportRepository


async def run_daily_pipeline(session_type: str = "morning"):
    """执行指定时段的日报生成流程"""
    print(f"[{datetime.now()}] 开始执行 {session_type} 日报流程...")

    # 步骤 1：运行 Agent
    agent = build_agent()
    result = await agent.ainvoke({
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "session_type": session_type,
        "title": "",
        "raw_articles": [],
        "processed_articles": [],
        "selected_article_ids": [],
        "sections": [],
        "editor_notes": "",
        "status": "draft",
    }, {"configurable": {"thread_id": f"daily-{session_type}"}})

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
                    "metadata": json.dumps(a.get("metadata", {}), ensure_ascii=False),
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
        prefix = "AI早报" if session_type == "morning" else "AI晚报"
        title = result.get("title", f"{prefix} · {today}")
        report_id = await report_repo.create(today, title, session_type)
        await report_repo.update(report_id, {
            "article_order": article_ids,
            "sections": result.get("sections", []),
            "editor_notes": result.get("editor_notes", ""),
            "total_articles": len(article_ids),
            "status": "published",
        })

    print(f"[{datetime.now()}] {session_type}日报流程完成。共发布 {len(article_ids)} 篇文章。")


def start_scheduler():
    """启动定时调度器（双时段：早报 + 晚报）"""
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    pub = config.get("app", {}).get("publish", {})
    morning = pub.get("morning", {"hour": 7, "minute": 0})
    evening = pub.get("evening", {"hour": 21, "minute": 0})

    scheduler.add_job(run_daily_pipeline, "cron", hour=morning["hour"], minute=morning["minute"], args=["morning"])
    scheduler.add_job(run_daily_pipeline, "cron", hour=evening["hour"], minute=evening["minute"], args=["evening"])

    scheduler.start()
    print(f"调度器已启动。早报 {morning['hour']:02d}:{morning['minute']:02d} / 晚报 {evening['hour']:02d}:{evening['minute']:02d}")

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    start_scheduler()
