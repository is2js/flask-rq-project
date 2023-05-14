from opengraph_py3 import OpenGraph

from app.rss_sources.config import SourceConfig
from .parser import RssParser
from .templates import TITLE_TEMPLATE, TABLE_START, TABLE_END
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
                # [카테고리 필터링] 카테고리가 일치하지 않으면 해당feed dict 넘어가기
                # - URLSource는 제외
                if issubclass(self.__class__, TargetSource) and category and not self._is_category(feed, category):
                    continue

                # [추가삽입] 부모인 source정보 삽입 -> DB적용시 source의 id로 대체?!
                #  - html에 표시할 때 prefix로 쓸 듯?!
                feed['source_name'] = self.NAME
                feed['source_url'] = self.URL

                # [변형/추출] cls별 재정의한 map 적용
                #  1) Tistory + Naver: thumbnail_url 추가 추출 등
                feed = self.map(feed)

                feeds.append(feed)

            total_feeds.extend(feeds)

        return total_feeds

    @staticmethod
    def _is_category(feed, category):
        return feed['category'] == category

    def map(self, feed):
        return feed

    @staticmethod
    def _get_og_image_url(current_url):

        og = OpenGraph(current_url, features='html.parser')
        if not og.is_valid():
            return None

        return og.get('image', None)





class URLSource(BaseSource):
    def __init__(self, urls):
        super().__init__()
        self._url_with_categories = self.check_category(self.check_type(urls))


class TargetSource(BaseSource):
    TARGET_URL = ''

    def __init__(self, target_id_with_categories):
        super().__init__()
        self.target_id_with_categories = self.check_category(self.check_type(target_id_with_categories))
        self._url_with_categories = self._generate_urls(self.target_id_with_categories)

    # def _generate_urls(self, target_ids):
    #     raise NotImplementedError

    def _generate_urls(self, target_id_and_categories):
        """
        :param target_id_and_categories: ('nittaku', 'IT게시판')
        :return:
        """

        target_urls = []
        for target_id, category in target_id_and_categories:
            if not target_id:
                # continue
                raise ValueError(f'{self.__class__.__name__}() 생성시 target_id가 없을 수 없습니다: {target_id}')

            target_url = self._get_target_url_from_id(target_id)
            target_urls.append((target_url, category))
        return target_urls

    def _get_target_url_from_id(self, target_id):
        return self.TARGET_URL.format(target_id)
