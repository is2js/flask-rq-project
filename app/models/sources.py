import pytz
from sqlalchemy import func, and_, or_, case
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, joinedload

from .base import BaseModel, db, transaction


class SourceCategory(BaseModel):
    """
    Youtube, Blog, URL
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True, index=True)

    sources = relationship('Source', back_populates='source_category', cascade='all, delete-orphan')

    @classmethod
    def get_list_with_source_count_and_names(cls):
        # .with_entities(cls, func.count(Source.id), func.group_concat(Source.target_name, '</br>')) \
        get_list_with_count_and_source_names = cls.query \
            .outerjoin(cls.sources) \
            .filter(cls.source_config_filter()) \
            .with_entities(cls, func.count(Source.id), func.group_concat(Source.target_name, '</br>')) \
            .group_by(cls.id) \
            .all()
        #  [(<SourceCategory object at 0x7f3250a74f40>, 2, '쌍보네TV</br>조재성'), (<SourceCategory object at 0x7f3250a74b80>, 2, '동신한의</br>is2js의블로그')]
        return get_list_with_count_and_source_names

    @classmethod
    def source_config_filter(cls):
        _Source = cls.sources.mapper.class_

        from app.rss_sources import SourceConfig

        target_filter = case(
            (
                cls.name == "Youtube",
                or_(_Source.target_url.contains(target_id) for target_id in SourceConfig.youtube_target_ids if
                    target_id)
            ),
            (
                cls.name == "Blog",
                or_(*[_Source.target_url.contains(target_id) for target_id, category in
                      SourceConfig.tistory_target_id_and_categories + SourceConfig.naver_target_id_and_categories
                      if target_id])),
            (
                cls.name == "URL",
                or_(*[_Source.name.__eq__(target_name) for target_url, target_name in SourceConfig.url_and_names if
                      target_name])),
            else_=None
        )

        return target_filter


class Source(BaseModel):
    """
    Youtube - 1,2,3                             => 1,2,3이 쓰임 (target_name, target_url in parser.parse)
    Blog - (Tistory) 1,2,3, + (Naver) 1,2,3,,   => ()가쓰임 (source_name, source_url in BaseSource.fetch_feeds)
    URL - 1,2,3                                 => 1,2,3이 쓰임
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)  # 사용자입력 NAME ex> Tistory, Naver, 유튜브, 왓챠
    url = db.Column(db.Text, nullable=False)
    # category = db.Column(db.Text, nullable=True)

    target_name = db.Column(db.Text, nullable=False)  # RSS타겟 NAME ex> xxx님의 blog, 쌍보네TV
    target_url = db.Column(db.Text, nullable=False, index=True, unique=True)

    source_category_id = db.Column(db.Integer, db.ForeignKey('sourcecategory.id', ondelete="CASCADE"))
    source_category = relationship('SourceCategory', foreign_keys=[source_category_id], back_populates='sources',
                                   uselist=False)

    feeds = relationship('Feed', back_populates='source', cascade='all, delete-orphan')


class Feed(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False, index=True)
    thumbnail_url = db.Column(db.Text, nullable=True)
    category = db.Column(db.Text, nullable=True)
    body = db.Column(db.Text, nullable=True)
    published = db.Column(db.DateTime(timezone=True))
    published_string = db.Column(db.Text, nullable=True)

    source_id = db.Column(db.Integer, db.ForeignKey('source.id', ondelete="CASCADE"))
    source = relationship('Source', foreign_keys=[source_id], back_populates='feeds', uselist=False)

    @property
    def published_timestamp(self):
        return self.published.timestamp() if self.published else None

    @property
    def kst_published(self):
        kst_tz = pytz.timezone('Asia/Seoul')
        utc_dt = self.published.replace(tzinfo=pytz.UTC)
        kst_dt = utc_dt.astimezone(kst_tz)
        return kst_dt