"""Agent 用 LLM 自主选文：从原始文章池中挑选最值得处理的 15 篇"""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

SELECT_PROMPT = """你是一位 AI 新闻主编。今天{time}，你需要从以下文章池中选择 {count} 篇。

选文标准：
1. 重要性：对 AI 行业影响越大越优先
2. 时效性：最新事件优先
3. 多样性：覆盖不同子话题，避免全是同一类
4. 独家性：独家消息优先于综合报道
5. 来源平衡：不同来源都要有

请从以下文章中选择最值得报道的 {count} 篇，返回 JSON 数组：
["标题1", "标题5", "标题12", ...]

文章列表：
{articles}

只返回 JSON 数组，不要其他文字。"""


async def select_articles(articles: list[dict], session_type: str = "morning") -> list[dict]:
    """用 LLM 从文章池中挑选最值得处理的文章"""
    if not articles:
        return []

    # 构建文章列表文本
    lines = []
    for i, a in enumerate(articles):
        title = a.get("title", "")
        source = a.get("source", "")
        lines.append(f"[{i}] [{source}] {title}")

    article_text = "\n".join(lines)
    count = min(15, len(articles))
    time_desc = "早报时段" if session_type == "morning" else "晚报时段"

    prompt = SELECT_PROMPT.format(time=time_desc, count=count, articles=article_text)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            indices = json.loads(content)
            if isinstance(indices, dict):
                # 兼容 { "selected": [0, 3, 5] } 格式
                for v in indices.values():
                    if isinstance(v, list):
                        indices = v
                        break
            result = [articles[i] for i in indices if isinstance(i, int) and 0 <= i < len(articles)]
            # 也兼容 ["标题1", "标题5"] 格式 → 按标题匹配
            if not result and isinstance(indices, list) and all(isinstance(x, str) for x in indices):
                title_map = {a.get("title", ""): a for a in articles}
                result = [title_map[t] for t in indices if t in title_map]
            return result[:15]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            print(f"[selector] LLM 选文失败: {e}，取前 {count} 篇兜底")
            return articles[:count]
