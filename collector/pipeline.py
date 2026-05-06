import yaml
from collector.base import RawArticle
from collector.scrapers import SCRAPERS


class CollectorPipeline:
    """采集管道：遍历所有启用的数据源并执行采集"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.max_per_source = self.config["collector"]["max_articles_per_source"]

    async def run(self) -> list[RawArticle]:
        all_articles = []
        sources = self.config["collector"]["sources"]

        for name, source_cfg in sources.items():
            if not source_cfg.get("enabled", False):
                continue
            scraper_cls = SCRAPERS.get(name)
            if not scraper_cls:
                print(f"未知数据源: {name}")
                continue
            scraper = scraper_cls(source_cfg)
            try:
                articles = await scraper.scrape()
                articles = articles[:self.max_per_source]
                all_articles.extend(articles)
                print(f"{name}: {len(articles)} 篇采集完成")
            except Exception as e:
                print(f"{name} 采集器执行失败: {e}")

        print(f"本轮采集总计: {len(all_articles)} 篇文章")
        return all_articles
