import pytz
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.rss_sources.config import SourceConfig
from app.models import Source, SourceCategory, Feed
from app.rss_sources.templates import TITLE_TEMPLATE, TABLE_START, TABLE_END, YOUTUBE_CUSTOM_TEMPLATE
from app.utils import parse_logger
from app.rss_sources.sources.blogs import *
from app.rss_sources.sources.youtube import *
from app.rss_sources.sources.urls import *
from app import session


class Markdown:

    def __init__(self, sources):
        self.sources = sources \
            if isinstance(sources, list) else [sources]

    def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):


        is_updated = self.fetch_new_feeds()

        # new_feeds = self.sort_and_truncate_feeds(feeds, display_numbers=display_numbers)

        # 현재 cls기준으로 source_category_name을 얻어낸다.
        source_category_name = self.get_source_category_name()
        # TargetSource라면, target_id list가 / URLSource라면 name list를 가져와서, 필터링에 사용할 것이다.
        target_id_or_name_list = self.get_target_or_name_list(source_category_name)

        # source_category_name와 target_id_or_name_list를 이용해서 필터링된 Feed를 가져온다.
        # Feed를 가져올건데, 관계필터링을 위해 Source와 SouceCategory를 innerjoin한다
        feeds = self.get_feeds(source_category_name, target_id_or_name_list, display_numbers)

        print([f.title for f in feeds])

        # updated_at = pytz.timezone('Asia/Seoul').localize(datetime.now())
        # kst로 바로 localize하니까, strftime이 안찍히는 듯
        utc_updated_at = pytz.utc.localize(datetime.utcnow())
        kst_updated_at = utc_updated_at.astimezone(pytz.timezone('Asia/Seoul'))
        markdown_text = ''
        markdown_text += TITLE_TEMPLATE.format(title_level, title, kst_updated_at.strftime("%Y-%m-%d %H:%M:%S"))
        markdown_text += self.set_custom()
        markdown_text += TABLE_START
        markdown_text += self.set_feed_template(feed_template, feeds, prefix=self.is_many_sources_or_targets())
        markdown_text += TABLE_END

        return markdown_text

    def fetch_new_feeds(self):
        new_feeds = []
        for source in self.sources:
            # request 작업
            fetch_feeds = source.fetch_feeds()
            # DB 작업
            for feed in fetch_feeds:
                # 0) db로의 처리를 위해 sourcecategory / source / feed 형태 잡아주기
                # - SourceCategory정보를 feed['source']내부 source_category 객체로 만들어주기 ( 임시 )
                feed['source']['source_category'] = SourceCategory.get_or_create(
                    name=self.get_source_category_name()
                )
                # - source dict를 Source객체로 바꿔주기 + url로만 존재여부 판단하기

                feed['source'] = Source.get_or_create(**feed['source'], get_key='target_url')

                # 1) url로 필터링 + title이 달라질 경우는 update
                prev_feed = Feed.query.filter_by(url=feed['url']).first()
                if prev_feed:
                    if feed['title'] != prev_feed.title:
                        prev_feed.update(**feed)
                    continue

                new_feeds.append(Feed(**feed))

        if new_feeds:
            parse_logger.info(f'{self.__class__.__name__}에서 new feed 발견')
            session.add_all(new_feeds)
            session.commit()
            return True
        else:
            parse_logger.info(f'{self.__class__.__name__}에서 새로운 feed가 발견되지 않았습니다')
            return False

    def get_source_category_name(self):
        return self.__class__.__name__.replace('Markdown', '')

    def get_target_or_name_list(self, source_category_name):
        # if 존재하는 것만 골라온다.
        if source_category_name == 'Blog':
            target_id_or_name_list = [target_id for target_id, category
                                      in
                                      SourceConfig.tistory_target_id_and_categories + SourceConfig.naver_target_id_and_categories
                                      if target_id]
        elif source_category_name == 'Youtube':
            target_id_or_name_list = [target_id for target_id in SourceConfig.youtube_target_ids if target_id]
        else:
            target_id_or_name_list = [target_name for target_url, target_name in SourceConfig.url_and_names if
                                      target_name]
        return target_id_or_name_list

    def get_feeds(self, source_category_name, target_id_or_name_list, display_numbers):
        filter_clause = self.create_feed_filter_clause(source_category_name, target_id_or_name_list)
        # join -> 관계필터링 용
        # options(joinedlload) -> view에서 부모 객체 사용을 위함.
        feeds = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(filter_clause) \
            .order_by(Feed.published.desc()) \
            .limit(display_numbers) \
            .all()
        return feeds

    def create_feed_filter_clause(self, source_category_name, target_id_or_name_list):
        # WHERE sourcecategory.name = ? AND (
        #           (source.target_url LIKE '%' || ? || '%') OR
        #           (source.target_url LIKE '%' || ? || '%') OR
        #           source.name = ? OR
        #           source.name = ?)
        # 해당 SourceCategory에 있어야하며
        filter_clause = SourceCategory.name == source_category_name

        # target_id가 target_url에 포함되거나 => TargetSource용
        filter_clause = filter_clause & or_(
            *[Source.target_url.contains(target_id_or_name) for target_id_or_name in target_id_or_name_list])

        # target_name이 Source의 name과 일치 => URLSource용
        filter_clause = filter_clause | or_(
            *[Source.name.__eq__(target_id_or_name) for target_id_or_name in target_id_or_name_list])

        return filter_clause

    def is_many_sources_or_targets(self):
        if issubclass(self.__class__, URLMarkdown):
            return False

        # youtube의 경우, 1source고정이니, 여러 target-> prefix가 필요하다
        # 그외 tistory나 naver 둘중에 1개의 source만 취하는 경우 -> target이 여러개인 경우 필요하다?!
        if len(self.sources) == 1:
            return len(self.sources[0].target_id_with_categories) > 1
        # source가 여러개인 경우 -> naver + tistory -> prefix가 필요하다.
        elif len(self.sources) > 1:
            return True
        else:
            return False

    # @staticmethod
    # def sort_and_truncate_feeds(feeds, display_numbers):
    #     feeds.sort(key=lambda f: f['published'], reverse=True)
    #
    #     return feeds[:display_numbers]

    def set_custom(self, **kwargs):
        return ''

    def set_feed_template(self, feed_template, feeds, prefix=None):
        raise NotImplementedError


class YoutubeMarkdown(Markdown):
    def __init__(self, target_ids):
        if not target_ids:
            raise ValueError(f'YoutubeMarkdown에 입력된 target_ids들이 존재하지 않습니다.')
        super().__init__(Youtube(target_ids))

    def set_custom(self):
        custom_result = ''
        for source in self.sources:
            if len(source.target_id_with_categories) == 1 and source.target_id_with_categories[0][0].startswith('UC'):
                custom_button = YOUTUBE_CUSTOM_TEMPLATE.format(source.target_id_with_categories[0][0])
                custom_result += custom_button

        return custom_result

    def set_feed_template(self, feed_template, feeds, prefix=None):
        feed_template_result = ''

        for feed in feeds:
            feed_text = feed_template.format(
                feed.url, #feed['url'],
                feed.thumbnail_url,
                feed.url,
                feed.title,
                # f'<span style="color:black">{feed["source_category_name"]} | </span>' if prefix else '',
                f'<span style="color:black">{feed.source.target_name} | </span>' if prefix else '',
                feed.published_string
            )
            feed_template_result += feed_text

        return feed_template_result


class BlogMarkdown(Markdown):
    def __init__(self, tistory_targets=None, naver_targets=None):
        sources = []
        if self.check_targets(tistory_targets):
            sources.append(Tistory(tistory_targets))
        if self.check_targets(naver_targets):
            sources.append(Naver(naver_targets))

        if not sources:
            raise ValueError(f'BlogMarkdown에 입력된 target들이 존재하지 않습니다.')

        super().__init__(sources)

    @staticmethod
    def check_targets(targets):
        return [target_id for target_id, category in targets if target_id]

    def set_feed_template(self, feed_template, feeds, prefix=None):
        feed_template_result = ''

        for feed in feeds:
            feed_text = feed_template.format(
                feed.url,
                feed.thumbnail_url,
                feed.url,
                feed.title,
                f'{feed.source.name} | ' if prefix else '',
                feed.published_string
            )
            feed_template_result += feed_text

        return feed_template_result


class URLMarkdown(Markdown):

    def __init__(self, url_and_names):
        sources = [globals()[name](url) for url, name in url_and_names]
        if not sources:
            raise ValueError(f'URLMarkdown에 입력된 url_and_names들이 존재하지 않습니다.')
        super().__init__(sources)

    def set_custom(self):
        custom_result = ''

        name_list = Source.query.join(Source.source_category).filter(
            SourceCategory.name == self.get_source_category_name()
        ).all()

        name_list = [source.name for source in name_list]
        custom_result += f'''\
<div align="center">
    📢 <sup><sub><strong>구독대상:</strong> {', '.join(name_list)}</sub></sup>
</div>
'''
        return custom_result

    def set_feed_template(self, feed_template, feeds, prefix=None):
        feed_template_result = ''
        for feed in feeds:
            feed_text = feed_template.format(
                feed.source.url,
                feed.source.name,
                f"{feed.category}" if feed.category else '',
                feed.url,
                feed.title,
                feed.published_string
            )
            feed_template_result += feed_text

        return feed_template_result
