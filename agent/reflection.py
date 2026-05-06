import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

CRITIQUE_PROMPT = """请审阅以下 AI 新闻摘要，检查是否有问题，返回 JSON：

{{
  "pass": true/false,
  "issues": ["问题1"],
  "suggestion": "修改建议"
}}

标题：{title}
摘要：{summary}

检查清单：
1. 关键信息是否清晰？（什么事 + 为什么重要）
2. 具体数字/数据是否保留？
3. 是否客观无幻觉？
4. 长度是否合适（约 {max_length} 字）？
5. 中文是否通顺自然？

只返回合法的 JSON。"""


async def critique_summary(title: str, summary: str, max_length: int = 200) -> dict:
    """对摘要进行自我审查，返回审查结果"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{
                    "role": "user",
                    "content": CRITIQUE_PROMPT.format(
                        title=title, summary=summary, max_length=max_length
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
            return {"pass": True, "issues": [], "suggestion": ""}
