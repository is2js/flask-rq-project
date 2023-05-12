from pprint import pprint

from .parser import RssParser
from .utils import requests_url
from app.utils import parse_logger


class BaseSource:
    NAME = ''  # source 이름
    URL = ''  # source 자체 url (not rss)

    def __init__(self):
        self._url_with_categories = None
        self.parser = RssParser()

    @staticmethod
    def check_type(target_ids_or_urls):
        # 바깥 괄호는 list여야한다. (안쪽괄호가 tuple)
        # if not isinstance(target_ids_or_urls, (list, tuple, set)):
        if not isinstance(target_ids_or_urls, list):
            target_ids_or_urls = [target_ids_or_urls]

        return target_ids_or_urls

    @staticmethod
    def check_category(urls_or_url_with_categories):
        urls_with_category = []
        for element in urls_or_url_with_categories:
            if not isinstance(element, tuple):
                # category가 같이 안들어왔으면 None으로 채워준다.
                element = (element, None)

            urls_with_category.append(element)
        return urls_with_category

    @staticmethod
    def _is_category(feed, category):
        if feed['category'] != category:
            return None
        return feed

    def fetch_feeds(self):

        total_feeds = []

        # for url in self._urls:
        for url, category in self._url_with_categories:
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

                # [카테고리 필터링] 카테고리가 일치하지 않으면 해당feed dict 넘어가기
                if category and not self._is_category(feed, category):
                    continue

                feeds.append(feed)

            total_feeds.extend(feeds)

        return total_feeds


class URLSource(BaseSource):
    def __init__(self, urls):
        super().__init__()
        self._url_with_categories = self.check_category(self.check_type(urls))


class TargetSource(BaseSource):
    TARGET_URL = ''

    def __init__(self, target_ids):
        super().__init__()
        self._url_with_categories = self._generate_urls(self.check_category(self.check_type(target_ids)))

    # def _generate_urls(self, target_ids):
    #     raise NotImplemented

    def _generate_urls(self, target_id_and_categories):
        """
        :param target_id_and_categories: ('nittaku', 'IT게시판')
        :return:
        """
        # return list(map(lambda x: (f"https://{x[0]}.tistory.com/rss", x[1]), target_id_and_categories))
        return list(map(
            lambda id_and_category: (
                self._get_target_url_from_id(id_and_category[0]), id_and_category[1]),
            target_id_and_categories
        ))

    def _get_target_url_from_id(self, target_id):
        return self.TARGET_URL.format(target_id)

