from typing import Optional
import os
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
from collector.base import BaseScraper, RawArticle

load_dotenv()


class RSSScraper(BaseScraper):
    """通用 RSS 采集器"""

    async def scrape(self) -> list[RawArticle]:
        articles = []
        feed_urls = self.config.get("feed_urls", [])
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # 从环境变量读代理
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        client_kwargs = {"headers": headers, "timeout": 30.0, "follow_redirects": True}
        if proxy:
            client_kwargs["proxy"] = proxy

        async with httpx.AsyncClient(**client_kwargs) as client:
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

        # Atom 格式：<feed> → <entry>
        ns = ""
        if root.tag.endswith("feed"):
            ns = root.tag.replace("feed", "")  # 提取命名空间
            items = root.findall(f"{ns}entry")
            for entry in items:
                title = self._get_text(entry, f"{ns}title")
                link_el = entry.find(f"{ns}link")
                link = link_el.get("href") if link_el is not None else ""
                content_el = entry.find(f"{ns}content")
                description = content_el.text[:2000] if content_el is not None and content_el.text else ""
                if not title or not link:
                    continue
                if not self._is_ai_related(title, description):
                    continue
                articles.append(RawArticle(
                    title=title, url=link, source="rss", source_id=link,
                    raw_content=description or "",
                    metadata={"feed_url": feed_url},
                ))
            return articles

        # RSS 格式：<channel> → <item>
        channel = root.find("channel")
        if channel is not None:
            items = channel.findall("item")
            for item in items:
                title = self._get_text(item, "title")
                link = self._get_text(item, "link")
                description = self._get_text(item, "description")
                if not title or not link:
                    continue
                if not self._is_ai_related(title, description):
                    continue
                articles.append(RawArticle(
                    title=title, url=link, source="rss", source_id=link,
                    raw_content=description or "",
                    metadata={"feed_url": feed_url},
                ))

        return articles

    def _get_text(self, parent, tag: str) -> str:
        """安全获取子标签文本"""
        elem = parent.find(tag)
        return elem.text.strip() if elem is not None and elem.text else ""

    def _is_ai_related(self, title: str, description: str = "") -> bool:
        """判断文章是否真正与 AI 大模型相关

        同时检查标题和描述，描述匹配权重减半。
        """
        title_lower = title.lower()
        desc_lower = description.lower()[:500]

        # 强关键词（2分）：提到就是 AI 核心话题
        strong_kw = [
            "大模型", "llm", "gpt-", "gpt5", "claude", "openai", "chatgpt",
            "deepseek", "llama", "rag", "多模态", "sora", "gemini",
            "人工智能", "transformer", "diffusion",
            "langchain", "copilot", "qwen", "通义千问", "mistral",
            "anthropic", "hugging face",
            "token", "benchmark",
        ]

        # 中关键词（1分）：需要 AI 上下文
        medium_kw = [
            "ai模型", "ai应用", "ai助手", "ai原生", "ai智能",
            "ai芯片", "physical ai", "物理ai",
            "agent", "模型发布", "开源模型",
            "神经网络", "深度学习", "机器学习",
            "微调", "推理", "对齐", "上下文窗口",
            "embedding", "向量数据库",
        ]

        # 排除模式
        negative = ["available", "detail", "failed", "email", "trailing"]

        score = 0
        for kw in strong_kw:
            if kw.lower() in title_lower:
                score += 2
            elif kw.lower() in desc_lower:
                score += 1  # 描述匹配权重减半
        for kw in medium_kw:
            if kw.lower() in title_lower:
                score += 1
            elif kw.lower() in desc_lower:
                score += 0.5
        for nk in negative:
            if nk.lower() in title_lower:
                return False

        return score >= 2
