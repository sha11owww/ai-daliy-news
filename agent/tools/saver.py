"""Agent 自主保存，同日去重（跨天允许重复，因为 arXiv 每日更新）"""

import json
from datetime import date
from pathlib import Path


async def save_report(result: dict) -> dict:
    articles = result.get("processed_articles", [])
    seen = _load_seen_urls()
    deduped = [a for a in articles if a.get("url") not in seen]
    skipped = len(articles) - len(deduped)
    if skipped:
        print(f"[saver] 同日去重: {skipped} 篇重复, {len(deduped)} 篇新")
    result["processed_articles"] = deduped or articles
    db_ok = await _save_to_db(result)
    if db_ok:
        return {"status": "saved", "method": "database", "total": len(deduped or articles), "skipped": skipped}
    return await _save_to_json(result)


def _load_seen_urls() -> set:
    """只加载今日已有文章的 URL（防早晚重复，不跨天）"""
    seen = set()
    base = Path("data") / "reports" / date.today().isoformat()
    if not base.exists():
        return seen
    for session in ("morning", "evening"):
        p = base / f"{session}.json"
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
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
        st = result.get("session_type", "morning")
        today = date.today()
        title = result.get("title", f"AI{'早报' if st=='morning' else '晚报'} · {today}")
        async with async_session() as session:
            repo = ArticleRepository(session)
            rpt = ReportRepository(session)
            aids = []
            for a in articles:
                if a.get("status") in ("classified", "reviewed"):
                    aid = await repo.batch_insert([{
                        "title": a["title"], "url": a["url"], "source": a["source"],
                        "source_id": a.get("source_id", ""), "raw_content": a.get("raw_content", ""),
                        "metadata": json.dumps(a.get("metadata", {}), ensure_ascii=False),
                    }])
                    if aid:
                        await repo.update_article(aid[0], {
                            "summary": a.get("summary", ""), "brief": a.get("brief", ""),
                            "tags": a.get("tags", []), "section": a.get("section"),
                            "importance_score": a.get("importance_score", 3),
                            "status": "published", "published_date": today,
                        })
                        aids.append(aid[0])
            rid = await rpt.create(today, title, st)
            await rpt.update(rid, {"article_order": aids, "sections": result.get("sections", []),
                "editor_notes": result.get("editor_notes", ""), "total_articles": len(aids), "status": "published"})
        print(f"[saver] DB 写入 {len(aids)} 篇")
        return True
    except Exception as e:
        print(f"[saver] DB 不可用: {e}")
        return False


async def _save_to_json(result: dict) -> dict:
    articles = result.get("processed_articles", [])
    today = date.today()
    ds = today.isoformat()
    st = result.get("session_type", "morning")
    prefix = "AI早报" if st == "morning" else "AI晚报"
    title = result.get("title", f"{prefix} · {today.strftime('%Y年%m月%d日')}")
    output = {
        "report_date": ds, "session_type": st, "title": title,
        "total_articles": len(articles), "sections": result.get("sections", []),
        "editor_notes": result.get("editor_notes", ""), "status": "published",
        "generated_at": str(datetime.now()),
        "articles": [{"title": a.get("title", ""), "url": a.get("url", ""), "source": a.get("source", ""),
            "summary": a.get("summary", ""), "brief": a.get("brief", ""),
            "tags": a.get("tags", []), "section": a.get("section"),
            "importance_score": a.get("importance_score", 3), "published_date": ds,
        } for a in articles],
    }
    from datetime import datetime
    data_dir = Path("data") / "reports" / ds
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / f"{st}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    idx = Path("data") / "reports" / "index.json"
    ix = json.load(open(idx, "r", encoding="utf-8")) if idx.exists() else []
    ix = [e for e in ix if not (e["date"] == ds and e["session"] == st)]
    ix.append({"date": ds, "session": st, "title": title, "total_articles": len(articles), "generated_at": output["generated_at"]})
    ix.sort(key=lambda x: x["date"], reverse=True)
    with open(idx, "w", encoding="utf-8") as f:
        json.dump(ix, f, ensure_ascii=False, indent=2)
    print(f"[saver] JSON {len(articles)} 篇: {data_dir}/{st}.json")
    return {"status": "saved", "method": "json", "path": str(data_dir / f"{st}.json"), "total": len(articles), "skipped": 0}
