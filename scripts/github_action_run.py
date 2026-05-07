#!/usr/bin/env python3
"""GitHub Actions 运行脚本：Agent 完全自主执行（含自动保存）"""

import asyncio
import os
import sys
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="morning", choices=["morning", "evening"])
    args = parser.parse_args()

    session_type = args.session
    today = date.today()
    prefix = "AI早报" if session_type == "morning" else "AI晚报"
    print(f"开始生成 {prefix} · {today}...")

    from agent.graph import build_agent
    agent = build_agent()

    await agent.ainvoke(
        {
            "report_date": today.isoformat(),
            "session_type": session_type,
            "title": "",
            "raw_articles": [],
            "processed_articles": [],
            "selected_article_ids": [],
            "sections": [],
            "editor_notes": "",
            "status": "draft",
        },
        {"configurable": {"thread_id": f"github-{session_type}-{today.isoformat()}"}},
    )

    print(f"\n✅ {prefix} · {today} 生成完成")


if __name__ == "__main__":
    asyncio.run(run())
