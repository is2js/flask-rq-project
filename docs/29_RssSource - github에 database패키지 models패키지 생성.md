### model을 고려하여, targets -> blogs + youtube로 패키지 나누기
1. targets 패키지를 `blogs`로 변경하고
2. youtube 패키지를 만들어, youtube.py를 만들고 init에 import한다
3. markdown_creator.py에서는 `from targets import *`를 blos, youtube 에서 import하도록 바꾼다.
    ```python
    # app/rss_sources/markdown_creator.py
    from blogs import *
    from youtube import *
    from urls import *
    
    
    class Markdown:
        #...
    ```
   

### 분석
- Source별(Blog, Youtube, URL) feed들을 보관해야한다?!
  - fetch_feeds시, 각 source정보가 없으면 create, 있으면 get한다?!
  - source모델이 존재해야, 각 source별 데이터를 쉽게 얻고 조회한다?
  - **아니라면, 직접 매번 feed모델의 source_category_name을 검색조건에 포함해야한다.**


1. 일단 Source로 분리하기 전에 Feed정보를 모아본다
    - parser.parse() 내부
        -  source_title: 개별source name(youtube prefix)
        -  source_link : rss http url -> X
        -  url
        -  category
        -  title
        -  thumbnail_url
        -  body
        -  published
        -  published_string
   - fetch_feeds() 내부
        - source_name: 사용자입력 NAME(blog prefix)
        - source_url: 사용자입력 http URL(url link)

2. 사실상 source_name은 source의 category느낌이고, source_title이 source_name느낌이다.
    - `SourceCategory` -> source_name, source_url from `Source cls의 NAME, URL 사용자입력`
    - `Source` -> source_category_id(fk), source_title, source_link 
    - `SourceFeed` -> source_id(fk), 나머지필드


#### 분석에 따른 필드명 변경
1. 아래와 같이 model별 필요한 필드를 구분한다
    - source_name -> source_category_name
    - source_url -> source_category_url
    - source_link -> source_url
    - source_title -> source_name

### github action용에만 database세팅하기
- 기존 프로젝트 참고: https://github.com/is2js/2022_sqlalchemy/blob/master/src/infra/config/base.py

1. rss_sources/database 패키지를 만들고, `base.py`내부에 `Base객체, session`에 대한 세팅을 끝낸다.
    - 그 과정에서 `sqlalchemy`를 설치하고 `pip freeze`까지 한다
    ```python
    # rss_sources/database/base.py 
    from sqlalchemy import MetaData, create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import scoped_session, sessionmaker
    
    from rss_sources import SourceConfig
    
    # sqlite migrate 오류시 발생할 수 있는 버그 픽스
    naming_convention = {
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(column_0_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
    
    Base = declarative_base()
    Base.metadata = MetaData(naming_convention=naming_convention)
    
    engine = create_engine(SourceConfig.DATABASE_URL, **SourceConfig.SQLALCHEMY_POOL_OPTIONS)
    session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    Base.query = session.query_property()
    ``` 

2. 2가지 세팅을 SourceConfig에 넣어준다.
    ```python
    # rss_sources/config.py 
    class SourceConfig:
        # ...
        # DB 설정
        DATABASE_URL = os.getenv('DATABASE_URL') or 'sqlite:///db.sqlite'
        SQLALCHEMY_POOL_OPTIONS = {
            'pool_size': 3,
            'pool_recycle': 55,  # # ClearDB's idle limit is 90 seconds, so set the recycle to be under 90
            'pool_timeout': 5,
            'max_overflow': 10
        }
    ```
### models패키지 만들고 각 model 형성
#### base작성
1. rss_sources/models패키지를 만들고, `base_model.py`를 만든다.
    - **BaseModel 정의시 테이블이름이 자동으로 적용되게`declared_attr`를 활용한다**
    - database.base.py에 있는 `Base객체기반`, `session객체기반`으로 BaseModel을 만든다.
    -`transaction` decorator를 만들어 기본메서드시 사용되게 한다..
    - **utils.py에 `db_logger 객체`를 만들어서, transaction내부에서 사용하게 한다.**
    - **DateTime객체는 db.DateTime(`timezone=True`)옵션을 주고 사용하며 `datetime.utcnow()`로 default를 사용한다**
    ```python
    # rss_sources/utils.py
    parse_logger = Logger("parse").getLogger
    db_logger = Logger("db").getLogger
    ```
    ```python
    from datetime import datetime
    from functools import wraps
    
    from rss_sources.database.base import session, Base
    import sqlalchemy as db
    from rss_sources.utils import db_logger
    
    def transaction(f):
        """ Decorator for database (session) transactions."""
    
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                value = f(*args, **kwargs)
    
                session.commit()
                return value
            except Exception as e:
                session.rollback()
                # raise
                db_logger.error(f'{str(e)}')
    
        return wrapper
    
    
    class BaseModel(Base):
        __abstract__ = True
    
        @declared_attr
        def __tablename__(cls) -> str:
            return cls.__name__.lower()
   
        created_at = db.Column(db.DateTime(timezone=True), nullable=True, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime(timezone=True), nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
    
        @classmethod
        @transaction
        def get_list(cls):
            items = cls.query.all()
            return items
    
        @transaction
        def save(self):
            session.add(self)
            return self
    
        @transaction
        def update(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            return self
    
        @transaction
        def delete(self):
            session.delete(self)
            return self
    
        def to_dict(self):
            data = dict()
    
            for col in self.__table__.columns:
                _key = col.name
                _value = getattr(self, _key)
                data[_key] = _value
    
            return data
    ```
   


#### model들 작성
- 참고: https://github1s.com/code-tutorials/python-feedreader/blob/master/models/source.py
- **passive_deletes옵션은 `부모삭제시 자식 남길 때 유용한 옵션`이라고 한다**
- 여기서는 category -> source -> feed 순으로 부모삭제시 같이 삭제되도록 한다

1. `source.py`를 만들어서, Category + Source를 같이 정의한다
    ```python
    from sqlalchemy.orm import relationship
    
    from .base import BaseModel, db
    
    
    class Category(BaseModel):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.Text, nullable=False)
        url = db.Column(db.Text, nullable=False, index=True)
    
        sources = relationship('Source', back_populates='category', cascade='all, delete-orphan')
    
    
    class Source(BaseModel):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.Text, nullable=False)
        url = db.Column(db.Text, nullable=False, index=True)
    
        category_id = db.Column(db.Integer, db.ForeignKey('category.id', ondelete="CASCADE"))
        category = relationship('Category', foreign_keys=[category_id], back_populates='sources')
    
        feeds = relationship('Feed', back_populates='source', cascade='all, delete-orphan')
    
    ```
   

2. `feed.py`를 만들어서 Feed를 정의한다.
    ```python
    from sqlalchemy.orm import relationship
    
    from .base import BaseModel, db
    
    
    class Feed(BaseModel):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.Text, nullable=False)
        url = db.Column(db.Text, nullable=False, index=True)
        thumbnail_url = db.Column(db.Text, nullable=True)
        body = db.Column(db.Text, nullable=True)
        published = db.Column(db.DateTime(timezone=True))
        published_string = db.Column(db.Text, nullable=True)
    
        source_id = db.Column(db.Integer, db.ForeignKey('source.id', ondelete="CASCADE"))
        source = relationship('Source', foreign_keys=[source_id], back_populates='feeds')
    
    ```
   


#### rss_sources의 init.py에 db파일이 없을 때 생성 메서드 -> manage.py에서 호출
1. init.py에 db생성코드 작성
    ```python
    def create_database():
        # rss_sources/__init__.py
        if not os.path.isfile(os.path.basename(SourceConfig.DATABASE_URL)):
            from rss_sources.models import Category, Source, Feed
            from rss_sources.database.base import Base, engine
            # print(os.path.basename(SourceConfig.DATABASE_URL))
            # db.sqlite
            Base.metadata.create_all(bind=engine)
    ```
2. manage.py에서 호출
    ```python
   # manage.py
    from rss_sources import get_youtube_markdown, get_blog_markdown, get_url_markdown, parse_logger, SourceConfig, \
        create_database
    
    create_database()
    ```
3. gitignore에 db파일 추가
    - `*.sqlite`
