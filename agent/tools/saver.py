"""Agent 自主保存工具：将日报结果持久化到数据库（兜底 JSON）"""

import json
import os
from datetime import datetime, date
from pathlib import Path


async def save_report(result: dict) -> dict:
    """保存日报结果到数据库（兜底写入 JSON 文件）

    作为 Agent 的最后一个工具，将 processed_articles 和日报结构
    持久化存储，使 Agent 完全自包含。
    """
    articles = result.get("processed_articles", [])
    sections = result.get("sections", [])
    session_type = result.get("session_type", "morning")
    today = date.today()

    # 尝试写入 PostgreSQL
    db_ok = await _save_to_db(result)
    if db_ok:
        return {"status": "saved", "method": "database", "total": len(articles)}

    # 兜底写入 JSON 文件
    return await _save_to_json(result)


async def _save_to_db(result: dict) -> bool:
    """尝试保存到数据库，失败返回 False"""
    try:
        from api.database import async_session
        from api.repositories.article_repo import ArticleRepository
        from api.repositories.report_repo import ReportRepository

        articles = result.get("processed_articles", [])
        session_type = result.get("session_type", "morning")
        today = date.today()
        title = result.get("title", f"AI{'早报' if session_type == 'morning' else '晚报'} · {today}")

        async with async_session() as session:
            article_repo = ArticleRepository(session)
            report_repo = ReportRepository(session)
            article_ids = []

            for a in articles:
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
                            "published_date": today,
                        })
                        article_ids.append(aid[0])

            report_id = await report_repo.create(today, title, session_type)
            await report_repo.update(report_id, {
                "article_order": article_ids,
                "sections": result.get("sections", []),
                "editor_notes": result.get("editor_notes", ""),
                "total_articles": len(article_ids),
                "status": "published",
            })

        print(f"[saver] 数据库写入成功: {len(article_ids)} 篇")
        return True
    except Exception as e:
        print(f"[saver] 数据库不可用，回退到 JSON: {e}")
        return False


async def _save_to_json(result: dict) -> dict:
    """兜底方案：写入 JSON 文件"""
    articles = result.get("processed_articles", [])
    sections = result.get("sections", [])
    session_type = result.get("session_type", "morning")
    today = date.today()
    date_str = today.isoformat()
    prefix = "AI早报" if session_type == "morning" else "AI晚报"
    title = result.get("title", f"{prefix} · {today.strftime('%Y年%m月%d日')}")

    output = {
        "report_date": date_str,
        "session_type": session_type,
        "title": title,
        "total_articles": len(articles),
        "sections": sections,
        "editor_notes": result.get("editor_notes", ""),
        "status": "published",
        "generated_at": datetime.now().isoformat(),
        "articles": [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("source", ""),
                "summary": a.get("summary", ""),
                "brief": a.get("brief", ""),
                "tags": a.get("tags", []),
                "section": a.get("section"),
                "importance_score": a.get("importance_score", 3),
            }
            for a in articles
        ],
    }

    data_dir = Path("data") / "reports" / date_str
    data_dir.mkdir(parents=True, exist_ok=True)

    report_file = data_dir / f"{session_type}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 更新索引
    index_path = Path("data") / "reports" / "index.json"
    index = []
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

    index = [e for e in index if not (e["date"] == date_str and e["session"] == session_type)]
    index.append({
        "date": date_str,
        "session": session_type,
        "title": title,
        "total_articles": len(articles),
        "generated_at": output["generated_at"],
    })
    index.sort(key=lambda x: x["date"], reverse=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[saver] JSON 写入成功: {report_file}")
    return {"status": "saved", "method": "json", "path": str(report_file), "total": len(articles)}
