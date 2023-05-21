from sqlalchemy.orm import relationship

from .base import BaseModel, db


class SourceCategory(BaseModel):
    """
    Youtube, Blog, URL
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True, index=True)

    sources = relationship('Source', back_populates='source_category', cascade='all, delete-orphan')


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
