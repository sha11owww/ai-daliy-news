#!/usr/bin/env python3
"""GitHub Actions 运行脚本：执行 Agent 流程并输出 JSON 文件"""

import asyncio
import json
import os
import argparse
from datetime import datetime, date
from pathlib import Path

# 从环境变量读取
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

if not API_KEY:
    print("错误: 未设置 DEEPSEEK_API_KEY 环境变量")
    exit(1)


async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="morning", choices=["morning", "evening"])
    args = parser.parse_args()

    session_type = args.session
    today = date.today()
    prefix = "AI早报" if session_type == "morning" else "AI晚报"
    title = f"{prefix} · {today.strftime('%Y年%m月%d日')}"
    date_str = today.isoformat()

    print(f"开始生成 {title}...")

    from agent.graph import build_agent
    agent = build_agent()

    result = await agent.ainvoke(
        {
            "report_date": date_str,
            "session_type": session_type,
            "title": "",
            "raw_articles": [],
            "processed_articles": [],
            "selected_article_ids": [],
            "sections": [],
            "editor_notes": "",
            "status": "draft",
        },
        {"configurable": {"thread_id": f"github-{session_type}-{date_str}"}},
    )

    articles = result.get("processed_articles", [])
    sections = result.get("sections", [])
    print(f"处理完成: {len(articles)} 篇文章, {len(sections)} 个栏目")

    # 构建输出数据
    output = {
        "report_date": date_str,
        "session_type": session_type,
        "title": title,
        "total_articles": len(articles),
        "sections": sections,
        "editor_notes": result.get("editor_notes", ""),
        "status": "published",
        "generated_at": datetime.now().isoformat(),
        "articles": [],
    }

    for a in articles:
        output["articles"].append({
            "id": a.get("id", 0),
            "title": a.get("title", ""),
            "url": a.get("url", ""),
            "source": a.get("source", ""),
            "summary": a.get("summary", ""),
            "brief": a.get("brief", ""),
            "tags": a.get("tags", []),
            "section": a.get("section"),
            "importance_score": a.get("importance_score", 3),
        })

    # 写入文件
    data_dir = Path("data") / "reports" / date_str
    data_dir.mkdir(parents=True, exist_ok=True)

    report_file = data_dir / f"{session_type}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"写入: {report_file}")

    # 更新索引
    index_path = Path("data") / "reports" / "index.json"
    index = []
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

    # 去重：同一日期的同一时段不重复记录
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
    print(f"索引更新: {len(index)} 条记录")

    print(f"\n✅ {title} 生成完成")


if __name__ == "__main__":
    asyncio.run(run())
