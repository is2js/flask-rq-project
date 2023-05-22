from app.models import Source
from sqlalchemy import or_
from app.rss_sources.config import SourceConfig
from app.rss_sources.services.base_service import SourceService
from app.rss_sources.sources.youtube import *
from app.rss_sources.templates import YOUTUBE_CUSTOM_TEMPLATE, YOUTUBE_FEED_TEMPLATE


class YoutubeService(SourceService):
    def __init__(self):
        if not SourceConfig.youtube_target_ids:
            raise ValueError(f'{self.__class__.__name__}에 대한 환경변수: YOUTUBE_TARGET_IDS가 존재하지 않습니다.')
        super().__init__(Youtube(SourceConfig.youtube_target_ids))

    def get_display_numbers(self):
        return SourceConfig.YOUTUBE_DISPLAY_NUMBERS

    def get_target_infos(self):
        return [target_id for target_id in SourceConfig.youtube_target_ids if target_id]

    def get_target_filter_clause(self, target_info_for_filter):
        return or_(*[Source.target_url.contains(target_id) for target_id in target_info_for_filter])

    def get_title(self):
        return SourceConfig.YOUTUBE_TITLE

    def set_custom(self):
        custom_result = ''

        target_ids = self.get_target_infos()
        if len(target_ids) == 1 and target_ids[0].startswith('UC'):
            custom_button = YOUTUBE_CUSTOM_TEMPLATE.format(target_ids[0])
            custom_result += custom_button

        return custom_result

    def set_feed_template(self, feeds):
        feed_template_result = ''

        for feed in feeds:
            feed_text = YOUTUBE_FEED_TEMPLATE.format(
                feed.url,  # feed['url'],
                feed.thumbnail_url,
                feed.url,
                feed.title,
                f'<span style="color:black">{feed.source.target_name} | </span>' if self.is_many_source() else '',
                feed.published_string
            )
            feed_template_result += feed_text

        return feed_template_result

