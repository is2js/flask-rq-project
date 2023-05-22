from app.models import Source
from sqlalchemy import or_

from app.rss_sources.templates import URL_FEED_TEMPLATE
from app.rss_sources.config import SourceConfig
from app.rss_sources.services.base_service import SourceService

from app.rss_sources.sources.urls import *


class URLService(SourceService):

    def __init__(self):
        if not SourceConfig.url_and_names:
            raise ValueError(f'{self.__class__.__name__}에 대한 환경변수 URL_NAME and URL_LIST 가 존재하지 않습니다.')

        sources = [globals()[name](url) for url, name in SourceConfig.url_and_names]
        # if not sources:
        #     raise ValueError(f'URLMarkdown에 입력된 url_and_names들이 존재하지 않습니다.')
        super().__init__(sources)

    def get_target_infos(self):
        return [target_name for target_url, target_name in SourceConfig.url_and_names if target_name]

    def get_display_numbers(self):
        return SourceConfig.URL_DISPLAY_NUMBERS

    def get_target_filter_clause(self, target_info_for_filter):
        return or_(
            *[Source.name.__eq__(target_name) for target_name in target_info_for_filter]
        )

    def get_title(self):
        return SourceConfig.URL_TITLE

    def set_custom(self):
        custom_result = ''

        custom_result += f'''\
<div align="center">
    📢 <sup><sub><strong>구독대상:</strong> {', '.join(self.get_target_infos())}</sub></sup>
</div>
'''
        return custom_result

    def set_feed_template(self, feeds):
        feed_template_result = ''

        for feed in feeds:
            feed_text = URL_FEED_TEMPLATE.format(
                feed.source.url,
                feed.source.name,
                f"{feed.category}" if feed.category else '',
                feed.url,
                feed.title,
                feed.published_string
            )
            feed_template_result += feed_text

        return feed_template_result
