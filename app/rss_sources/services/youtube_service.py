from app.models import Source
from app.rss_sources.config import SourceConfig
from app.rss_sources.services.base_service import SourceService
from app.rss_sources.sources.youtube import *


class YoutubeService(SourceService):
    def __init__(self):
        if not SourceConfig.youtube_target_ids:
            raise ValueError(f'{self.__class__.__name__}에 대한 환경변수: YOUTUBE_TARGET_IDS가 존재하지 않습니다.')
        super().__init__(Youtube(SourceConfig.youtube_target_ids))

    def get_display_numbers(self):
        return SourceConfig.YOUTUBE_DISPLAY_NUMBERS

    def get_target_info_for_filter(self):
        return [target_id for target_id in SourceConfig.youtube_target_ids if target_id]

    def get_target_filter_clause(self, target_info_for_filter):
        from sqlalchemy import or_
        return or_(*[Source.target_url.contains(target_id) for target_id in target_info_for_filter])
