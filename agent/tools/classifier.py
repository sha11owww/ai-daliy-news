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
