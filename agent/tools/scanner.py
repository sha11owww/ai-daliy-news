from collector.pipeline import CollectorPipeline


async def scan_sources(keywords: str | None = None) -> list[dict]:
    """扫描所有启用的数据源，返回文章列表

    编辑 Agent 用此工具获取当天的原始素材。
    """
    pipeline = CollectorPipeline()
    raw_articles = await pipeline.run()
    return [
        {
            "title": a.title,
            "url": a.url,
            "source": a.source,
            "source_id": a.source_id,
            "raw_content": a.raw_content,
            "metadata": a.metadata,
        }
        for a in raw_articles
    ]
