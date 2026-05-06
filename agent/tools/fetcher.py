import os
import httpx
from bs4 import BeautifulSoup


async def fetch_content(url: str) -> str:
    """抓取文章正文并清洗为纯文本"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    client_kwargs = {"headers": headers, "timeout": 30.0, "follow_redirects": True}
    if proxy:
        client_kwargs["proxy"] = proxy

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines[:200])
    except Exception as e:
        return f"抓取失败 {url}: {e}"
