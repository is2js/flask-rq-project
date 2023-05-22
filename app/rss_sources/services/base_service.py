from abc import abstractmethod

import pytz
from sqlalchemy.orm import joinedload

from app.models import SourceCategory, Source, Feed
from app.rss_sources.config import SourceConfig
from app.rss_sources.templates import TITLE_TEMPLATE, TABLE_START, TABLE_END
from app.utils import parse_logger
from app import session


class SourceService:

    def __init__(self, sources):
        self.sources = sources \
            if isinstance(sources, list) else [sources]

    def fetch_new_feeds(self):
        new_feeds = []
        for source in self.sources:
            # request 작업
            fetch_feeds = source.fetch_feeds()
            # DB 작업
            for feed in fetch_feeds:
                # 0) db로의 처리를 위해 sourcecategory / source / feed 형태 잡아주기
                feed['source']['source_category'] = SourceCategory.get_or_create(
                    name=self.get_source_category_name()
                )
                feed['source'] = Source.get_or_create(**feed['source'], get_key='target_url')

                # 1) url로 필터링 + title이 달라질 경우는 update
                prev_feed = Feed.query.filter_by(url=feed['url']).first()
                if prev_feed:
                    if feed['title'] != prev_feed.title:
                        prev_feed.update(**feed)
                    continue

                new_feeds.append(Feed(**feed))

        if new_feeds:
            parse_logger.info(f'{self.__class__.__name__}에서 new feed를 가져왔습니다.')

            session.add_all(new_feeds)
            session.commit()
            return new_feeds
        else:
            parse_logger.info(f'{self.__class__.__name__}에서 새로운 feed가 발견되지 않았습니다')
            session.rollback()
            return False

    def get_feeds(self):
        # SourceCategory 필터링
        source_category_name = self.get_source_category_name()
        # Source-target_url(Youtube, Blog) or name(URL) 및 Feed-category(Blog) 필터링
        target_info_for_filter = self.get_target_infos()
        display_numbers = self.get_display_numbers()

        feeds = self._get_feeds(source_category_name, target_info_for_filter, display_numbers)

        return feeds

    def get_source_category_name(self):
        return self.__class__.__name__.replace('Service', '')

    @abstractmethod
    def get_target_infos(self):
        raise NotImplementedError

    @abstractmethod
    def get_display_numbers(self):
        raise NotImplementedError

    def _get_feeds(self, source_category_name, target_infos, display_numbers):
        # cls별 개별 필터링 by source_category_name, target_info_for_filter
        filter_clause = self._create_feed_filter_clause(source_category_name, target_infos)

        feeds = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(filter_clause) \
            .order_by(Feed.published.desc()) \
            .limit(display_numbers) \
            .all()
        return feeds

    def _create_feed_filter_clause(self, source_category_name, target_infos):
        # WHERE sourcecategory.name = ? AND (
        #           (source.target_url LIKE '%' || ? || '%') OR
        #           (source.target_url LIKE '%' || ? || '%') OR
        #           source.name = ? OR
        #           source.name = ?)
        # => 분리해야됌.
        # => Youtube, Blog는 Sourcetarget_url에 target_id가 포함
        # => URL은 Source.name에 target_name이 포함
        # 해당 SourceCategory에 있어야하며
        filter_clause = SourceCategory.name == source_category_name

        # target_id가 target_url에 포함되거나 => TargetSource용
        # target_name이 Source의 name과 일치 => URLSource용
        #     by self.get_target_filter_clause 개별구현
        filter_clause = filter_clause & self.get_target_filter_clause(target_infos)

        return filter_clause

    @abstractmethod
    def get_target_filter_clause(self, target_infos):
        raise NotImplementedError


    def render(self, title_level=SourceConfig.TITLE_LEVEL):
        # updated_at = pytz.timezone('Asia/Seoul').localize(datetime.now())
        # kst로 바로 localize하니까, strftime이 안찍히는 듯
        from datetime import datetime
        utc_updated_at = pytz.utc.localize(datetime.utcnow())
        kst_updated_at = utc_updated_at.astimezone(pytz.timezone('Asia/Seoul'))
        markdown_text = ''
        markdown_text += TITLE_TEMPLATE.format(title_level, self.get_title(),
                                               kst_updated_at.strftime("%Y-%m-%d %H:%M:%S"))
        markdown_text += self.set_custom()
        markdown_text += TABLE_START
        markdown_text += self.set_feed_template(self.get_feeds())
        markdown_text += TABLE_END

        return markdown_text

    def is_many_source(self):
        return len(self.get_target_infos()) > 1

    def set_custom(self):
        return ''

    @abstractmethod
    def get_title(self):
        raise NotImplementedError

    @abstractmethod
    def set_feed_template(self, feeds):
        raise NotImplementedError
