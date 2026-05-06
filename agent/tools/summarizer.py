import os
import httpx
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
