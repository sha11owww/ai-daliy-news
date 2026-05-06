from typing import Optional
from collector.base import BaseScraper, RawArticle


class RedditScraper(BaseScraper):
    """Reddit 采集器（需配置 API 密钥）"""

    async def scrape(self) -> list[RawArticle]:
        import asyncpraw

        reddit = asyncpraw.Reddit(
            client_id=self.config.get("client_id", ""),
            client_secret=self.config.get("client_secret", ""),
            user_agent=self.config.get("user_agent", "ai-daily/1.0"),
        )

        articles = []
        subreddits = self.config.get("subreddits", ["artificial", "MachineLearning", "LocalLLaMA"])

        for sub_name in subreddits:
            try:
                sub = await reddit.subreddit(sub_name)
                async for submission in sub.hot(limit=15):
                    article = self._parse_submission(submission)
                    if article:
                        articles.append(article)
            except Exception as e:
                print(f"Reddit r/{sub_name} 采集失败: {e}")

        await reddit.close()
        print(f"Reddit: 采集到 {len(articles)} 篇文章")
        return articles

    def _parse_submission(self, submission) -> Optional[RawArticle]:
        if not self._is_ai_related(submission.title):
            return None

        return RawArticle(
            title=submission.title,
            url=submission.url,
            source="reddit",
            source_id=submission.id,
            raw_content=getattr(submission, "selftext", ""),
            metadata={
                "score": submission.score,
                "num_comments": submission.num_comments,
                "subreddit": str(submission.subreddit),
                "permalink": f"https://reddit.com{submission.permalink}",
            },
        )

    def _is_ai_related(self, title: str) -> bool:
        keywords = [
            "ai", "llm", "gpt", "claude", "openai", "deepseek", "llama",
            "rag", "agent", "machine learning", "deep learning", "transformer",
            "diffusion", "langchain", "copilot", "chatgpt", "gemini",
            "mistral", "qwen", "neural", "sora", "multimodal", "ml",
        ]
        lower = title.lower()
        return any(kw in lower for kw in keywords)
