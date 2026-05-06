from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawArticle:
    """原始文章数据结构"""
    title: str
    url: str
    source: str           # linuxdo/reddit/twitter
    source_id: str = ""
    raw_content: str = ""
    metadata: dict = field(default_factory=dict)


class BaseScraper(ABC):
    """采集器基类，所有来源采集器需继承此类"""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def scrape(self) -> list[RawArticle]:
        """执行采集，返回原始文章列表"""
        pass
