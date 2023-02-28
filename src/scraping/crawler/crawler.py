from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from time import sleep
from typing import Iterator, List, Callable

import feedparser
import lxml.html
import requests

from src.scraping.article import ArticleSource


class Crawler(Iterable, ABC):

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        """
        This should implement an iterator yielding crawled links
        :return: Iterator of links
        """
        raise NotImplementedError

    def crawl(self, delay: Callable[[], float] = lambda: 0.) -> Iterator[ArticleSource]:
        with requests.Session() as session:
            for url in self:
                sleep(delay())
                response = session.get(url=url)
                article_source = ArticleSource(url=response.url,
                                               html=response.text,
                                               crawl_date=datetime.now(),
                                               source=self)
                yield article_source


class StaticCrawler(Crawler):

    def __init__(self, links: List[str]):
        self.links = links

    def __iter__(self):
        yield from self.links


class RSSCrawler(Crawler):

    def __init__(self, url: str):
        self.url = url

    def __iter__(self) -> Iterator[str]:
        rss_feed = feedparser.parse(self.url)
        return [entry["link"] for entry in rss_feed['entries']]


class SitemapCrawler(Crawler):

    def __init__(self, sitemap: str, recursive: bool = True, reverse: bool = False):

        self.sitemap = sitemap
        self.recursive = recursive
        self.reverse = reverse

    def config(self, recursive: bool, reverse: bool):
        self.recursive = recursive
        self.reverse = reverse

    def __iter__(self) -> Iterator[str]:

        def yield_recursive(url: str):
            try:
                sitemap_html = session.get(url).content
            except Exception as err:
                raise err
            if not sitemap_html:
                return
            tree = lxml.html.fromstring(sitemap_html)
            urls = [node.text_content() for node in tree.cssselect('url > loc')]
            yield from reversed(urls) if self.reverse else urls
            if self.recursive:
                sitemap_locs = [node.text_content() for node in tree.cssselect('sitemap > loc')]
                for loc in reversed(sitemap_locs) if self.reverse else sitemap_locs:
                    yield from yield_recursive(loc)

        with requests.Session() as session:
            yield from yield_recursive(self.sitemap)