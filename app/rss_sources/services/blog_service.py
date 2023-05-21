from sqlalchemy import and_

from app.models import Source
from app.rss_sources.config import SourceConfig
from app.rss_sources.services.base_service import SourceService
from app.rss_sources.sources.blogs import *

class BlogService(SourceService):
    def __init__(self):

        if not (SourceConfig.tistory_target_id_and_categories or SourceConfig.naver_target_id_and_categories):
            raise ValueError(f'{self.__class__.__name__}에 대한 환경변수 TISTORY_TARGET_IDS or NAVER_TARGET_IDS가 존재하지 않습니다.')

        sources = []

        if SourceConfig.tistory_target_id_and_categories:
            sources.append(Tistory(SourceConfig.tistory_target_id_and_categories))
        if SourceConfig.naver_target_id_and_categories:
            sources.append(Naver(SourceConfig.naver_target_id_and_categories))

        # if not sources:
        #     raise ValueError(f'BlogMarkdown에 입력된 target들이 존재하지 않습니다.')

        super().__init__(sources)

    @staticmethod
    def filter_exist_targets(targets):
        return [target_id for target_id, category in targets if target_id]

    def get_display_numbers(self):
        return SourceConfig.BLOG_DISPLAY_NUMBERS

    def get_target_info_for_filter(self):

        return [(target_id, category) for target_id, category in
                SourceConfig.tistory_target_id_and_categories + SourceConfig.naver_target_id_and_categories
                if target_id]

    def get_target_filter_clause(self, target_info_for_filter):
        none_category_filter = lambda target_id : Source.target_url.contains(target_id)
        with_category_filter = lambda target_id, category : and_(Source.target_url.contains(target_id), Feed.category == category)
        from sqlalchemy import or_
        target_filter = or_(*[none_category_filter(target_id) if not category else with_category_filter(target_id, category) for target_id, category in target_info_for_filter])
        # print(target_info_for_filter)
        # print(target_filter)
        # [('nittaku', 'pythonic practice'), ('is2js', '마왕')]
        # (source.target_url LIKE '%' || :target_url_1 || '%') AND feed.category = :category_1 OR (source.target_url LIKE '%' || :target_url_2 || '%') AND feed.category = :category_2
        return target_filter
