from typing import Optional
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from collector.base import BaseScraper, RawArticle


class RSSScraper(BaseScraper):
    """通用 RSS 采集器"""

    async def scrape(self) -> list[RawArticle]:
        articles = []
        feed_urls = self.config.get("feed_urls", [])
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
            for feed_url in feed_urls:
                try:
                    resp = await client.get(feed_url)
                    if resp.status_code != 200:
                        print(f"RSS {feed_url} 返回 {resp.status_code}")
                        continue
                    items = self._parse_feed(resp.text, feed_url)
                    articles.extend(items)
                    print(f"RSS {feed_url}: {len(items)} 篇")
                except Exception as e:
                    print(f"RSS {feed_url} 采集失败: {e}")

        print(f"RSS: 采集到 {len(articles)} 篇文章")
        return articles

    def _parse_feed(self, content: str, feed_url: str) -> list[RawArticle]:
        """解析 RSS/Atom 订阅内容"""
        articles = []
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return articles

        # RSS 格式
        items = []
        channel = root.find("channel")
        if channel is not None:
            items = channel.findall("item")

        for item in items:
            title = self._get_text(item, "title")
            link = self._get_text(item, "link")
            description = self._get_text(item, "description")
            pub_date = self._get_text(item, "pubDate")

            if not title or not link:
                continue
            if not self._is_ai_related(title):
                continue

            articles.append(RawArticle(
                title=title,
                url=link,
                source="rss",
                source_id=link,
                raw_content=description or "",
                metadata={
                    "feed_url": feed_url,
                    "published": pub_date or "",
                },
            ))

        return articles

    def _get_text(self, parent, tag: str) -> str:
        """安全获取子标签文本"""
        elem = parent.find(tag)
        return elem.text.strip() if elem is not None and elem.text else ""

    def _is_ai_related(self, title: str) -> bool:
        """判断是否与 AI 相关"""
        keywords = [
            "ai", "人工智能", "llm", "大模型", "gpt", "claude", "openai",
            "deepseek", "llama", "rag", "agent", "机器学习", "深度学习",
            "神经网络", "transformer", "diffusion", "embedding", "vector",
            "langchain", "autogpt", "copilot", "chatgpt", "多模态",
            "sora", "gemini", "mistral", "qwen", "通义", "千问",
            "model", "neural", "robot", "自动化", "算法",
        ]
        lower = title.lower()
        return any(kw.lower() in lower for kw in keywords)
