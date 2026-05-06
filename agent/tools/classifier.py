import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

CLASSIFY_PROMPT = """你是一位 AI 新闻编辑。分析以下文章，返回 JSON：

{{
  "tags": ["标签1", "标签2"],
  "section": "栏目名",
  "importance_score": 1-5,
  "reason": "一句话说明为什么重要"
}}

重要度评分标准：
- 5 = 行业地震级（GPT 发布、大厂战略转型、重大技术突破）
- 4 = 重要动态（产品更新、融资、技术报告）
- 3 = 值得关注（趋势分析、行业讨论、常规更新）
- 2 = 普通资讯
- 1 = 边缘相关

栏目选择（必选其一，请根据文章核心内容判断，不要全归入行业重磅）：
- 行业重磅：仅限头条级大事、大厂重大官宣、行业里程碑事件。不要放普通产品更新或分析文章。
- 技术内核：基座模型、架构、MoE、RAG、Agent、记忆、工作流、论文、算法创新、评测基准、Token 优化、技术分析
- AIGC 多模态：绘画、视频、配音、多模态模型、生成类内容、图像/音频/视频生成
- 产品应用与工具：AI 新产品、插件、网站、客户端、企业落地案例、AI 硬件、行业应用
- 商业政策：融资并购 IPO、商业模式、监管法规、版权、安全伦理、国际政策

标题：{title}
内容：{content}

注意：不要把所有文章都归入"行业重磅"。普通产品更新归入"产品应用与工具"，纯技术讨论归入"技术内核"。

只返回合法的 JSON。"""


async def classify(article: dict) -> dict:
    """分类文章：打标签 + 归入栏目 + 评估重要度"""
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
                "max_tokens": 300,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        data = resp.json()
        try:
            result = json.loads(data["choices"][0]["message"]["content"])
            # 确保 section 是合法栏目名
            valid_sections = ["行业重磅", "技术内核", "AIGC 多模态", "产品应用与工具", "商业政策"]
            if result.get("section") not in valid_sections:
                result["section"] = "行业重磅"
            return result
        except (json.JSONDecodeError, KeyError):
            return {"tags": ["ai"], "section": "行业重磅", "importance_score": 3, "reason": "分类失败"}
