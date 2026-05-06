from .linuxdo import LinuxDOScraper
from .reddit import RedditScraper

SCRAPERS = {
    "linuxdo": LinuxDOScraper,
    "reddit": RedditScraper,
}
