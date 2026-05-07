"""Agent 自主保存工具，自动去重但始终生成日报（允许空报告）"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path


async def save_report(result: dict) -> dict:
    articles = result.get("processed_articles", [])
    session_type = result.get("session_type", "morning")

    seen = _load_seen_urls()
    deduped = [a for a in articles if a.get("url") not in seen]
    skipped = len(articles) - len(deduped)
    if skipped:
        print(f"[saver] 去重: {skipped} 篇重复, 保留 {len(deduped)} 篇新")
    # 即使全是重复，也生成日报（只是内容可能是空的）
    result["processed_articles"] = deduped or articles

    db_ok = await _save_to_db(result)
    if db_ok:
        return {"status": "saved", "method": "database", "total": len(deduped or articles), "skipped": skipped}
    return await _save_to_json(result)


def _load_seen_urls() -> set:
    seen = set()
    base = Path("data") / "reports"
    if not base.exists():
        return seen
    now = date.today()
    for i in range(7):
        d = now - timedelta(days=i)
        for session in ("morning", "evening"):
            path = base / d.isoformat() / f"{session}.json"
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for a in json.load(f).get("articles", []):
                            if a.get("url"):
                                seen.add(a["url"])
                except Exception:
                    pass
    return seen


async def _save_to_db(result: dict) -> bool:
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
                        "title": a["title"], "url": a["url"], "source": a["source"],
                        "source_id": a.get("source_id", ""), "raw_content": a.get("raw_content", ""),
                        "metadata": json.dumps(a.get("metadata", {}), ensure_ascii=False),
                    }])
                    if aid:
                        await article_repo.update_article(aid[0], {
                            "cleaned_text": a.get("cleaned_text", ""),
                            "summary": a.get("summary", ""), "brief": a.get("brief", ""),
                            "tags": a.get("tags", []), "section": a.get("section"),
                            "importance_score": a.get("importance_score", 3),
                            "status": "published", "published_date": today,
                        })
                        article_ids.append(aid[0])

            report_id = await report_repo.create(today, title, session_type)
            await report_repo.update(report_id, {
                "article_order": article_ids, "sections": result.get("sections", []),
                "editor_notes": result.get("editor_notes", ""),
                "total_articles": len(article_ids), "status": "published",
            })
        print(f"[saver] DB 写入 {len(article_ids)} 篇")
        return True
    except Exception as e:
        print(f"[saver] DB 不可用: {e}")
        return False


async def _save_to_json(result: dict) -> dict:
    articles = result.get("processed_articles", [])
    today = date.today()
    date_str = today.isoformat()
    session_type = result.get("session_type", "morning")
    prefix = "AI早报" if session_type == "morning" else "AI晚报"
    title = result.get("title", f"{prefix} · {today.strftime('%Y年%m月%d日')}")

    output = {
        "report_date": date_str, "session_type": session_type, "title": title,
        "total_articles": len(articles), "sections": result.get("sections", []),
        "editor_notes": result.get("editor_notes", ""), "status": "published",
        "generated_at": datetime.now().isoformat(),
        "articles": [{
            "title": a.get("title", ""), "url": a.get("url", ""), "source": a.get("source", ""),
            "summary": a.get("summary", ""), "brief": a.get("brief", ""),
            "tags": a.get("tags", []), "section": a.get("section"),
            "importance_score": a.get("importance_score", 3),
            "published_date": date_str,
        } for a in articles],
    }

    data_dir = Path("data") / "reports" / date_str
    data_dir.mkdir(parents=True, exist_ok=True)
    report_file = data_dir / f"{session_type}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    index_path = Path("data") / "reports" / "index.json"
    index = json.load(open(index_path, "r", encoding="utf-8")) if index_path.exists() else []
    index = [e for e in index if not (e["date"] == date_str and e["session"] == session_type)]
    index.append({"date": date_str, "session": session_type, "title": title, "total_articles": len(articles), "generated_at": output["generated_at"]})
    index.sort(key=lambda x: x["date"], reverse=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[saver] JSON 写入 {len(articles)} 篇: {report_file}")
    return {"status": "saved", "method": "json", "path": str(report_file), "total": len(articles), "skipped": 0}
