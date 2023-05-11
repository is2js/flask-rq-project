from pprint import pprint

from .parser import RssParser
from .utils import requests_url
from app.utils import parse_logger


class BaseSource:
    NAME = ''  # source 이름
    URL = ''  # source 자체 url (not rss)

    def __init__(self):
        self._urls = None
        self.parser = RssParser()

    @staticmethod
    def check_type(target_ids_or_urls):
        if not isinstance(target_ids_or_urls, (list, tuple, set)):
            target_ids_or_urls = [target_ids_or_urls]
        return target_ids_or_urls

    def convert_feed(self, feed):
        return feed

    def fetch_feeds(self):

        total_feeds = []

        for url in self._urls:
            result_text = requests_url(url)
            # [FAIL] 요청 실패시 넘어가기
            if not result_text:
                parse_logger.info(f'{self.__class__.__name__}의 url({url})에 대한 request요청에 실패')
                continue

            # [SUCCESS] 요청 성공시 parse(generate)로 feed dict 1개씩 받아 처리하기
            feeds = []
            for feed in self.parser.parse(result_text):
                # [추가삽입] 부모인 source정보 삽입 -> DB적용시 source의 id로 대체?!
                feed['source_name'] = self.NAME
                feed['source_url'] = self.URL

                feeds.append(feed)

            total_feeds.extend(feeds)

        return total_feeds


class URLSource(BaseSource):
    def __init__(self, urls):
        super().__init__()
        self._urls = self.check_type(urls)


class TargetSource(BaseSource):
    def __init__(self, target_ids):
        super().__init__()
        self._urls = self._generate_urls(self.check_type(target_ids))

    def _generate_urls(self, target_ids):
        raise NotImplemented
