from .linuxdo import LinuxDOScraper
from .reddit import RedditScraper
from .rss import RSSScraper

SCRAPERS = {
    "linuxdo": LinuxDOScraper,
    "reddit": RedditScraper,
    "rss": RSSScraper,
}
