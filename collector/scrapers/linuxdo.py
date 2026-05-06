from typing import Optional
from collector.base import BaseScraper, RawArticle


class LinuxDOScraper(BaseScraper):
    """LinuxDO 论坛采集器"""

    BASE_URL = "https://linux.do"

    async def scrape(self) -> list[RawArticle]:
        articles = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        import httpx
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            for cat_id in self.config.get("category_ids", [7, 32]):
                url = f"{self.BASE_URL}/categories/{cat_id}.json"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for topic in data.get("topic_list", {}).get("topics", [])[:20]:
                        article = self._parse_topic(topic, cat_id)
                        if article:
                            articles.append(article)
                except Exception as e:
                    print(f"LinuxDO 分类 {cat_id} 采集失败: {e}")

        print(f"LinuxDO: 采集到 {len(articles)} 篇文章")
        return articles

    def _parse_topic(self, topic: dict, category_id: int) -> Optional[RawArticle]:
        title = topic.get("title", "").strip()
        if not title or not self._is_ai_related(title):
            return None

        slug = topic.get("slug", "")
        topic_id = topic.get("id", "")
        url = f"{self.BASE_URL}/t/{slug}/{topic_id}" if slug else ""

        return RawArticle(
            title=title,
            url=url,
            source="linuxdo",
            source_id=str(topic_id),
            metadata={
                "category_id": category_id,
                "posts_count": topic.get("posts_count", 0),
                "created_at": topic.get("created_at", ""),
            },
        )

    def _is_ai_related(self, title: str) -> bool:
        keywords = [
            "ai", "人工智能", "llm", "大模型", "gpt", "claude", "openai",
            "deepseek", "llama", "rag", "agent", "机器学习", "深度学习",
            "神经网络", "transformer", "diffusion", "embedding", "vector",
            "langchain", "autogpt", "copilot", "chatgpt", "多模态",
            "sora", "gemini", "mistral", "qwen", "通义", "千问",
        ]
        lower = title.lower()
        return any(kw.lower() in lower for kw in keywords)
