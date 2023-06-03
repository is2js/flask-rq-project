### models들부터 옮기기
1. task관련 root/models.py를 models패키지를 만들고, tasks.py로 옮긴다
    - **이 때, models.py나 `models패키지/__init__.py`나 동일한 import루트를 가지게 된다**
2. tasks.py에 있는 Base관련 들을 `base.py`를 만들어서 옮긴다
    - **이 때, session과 Base는 기존 프로젝트 껏(app.session)을 사용한다**
    - github의 `base.py`도 기존 Model의 base에 통합한다
3. github의 feed, source, sourcecategory는 모두 feeds로 옮기자.
    ```python
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
        category = db.Column(db.Text, nullable=True)
    
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
    
    ```
    - init.py에 올린 뒤, app/init.py에 create_all()에도 올리자
    ```python
    from .tasks import Task, Notification, Message
    from .sources import Feed, Source, SourceCategory
    ```
   
### rss_source 옮기기
### rss_sources/init.py에서 테스트
1. github에서 쓰던 것 Markdown객체로 일단 테스트를 하려고 한다
   - 이 때, db.sqlite가 상대주소(`///db.sqlite`)로 생성되므로 rss_sources내부에서 만들어진다.
   - **Base객체, engine를 가져와 create_all(engine)을 해서 만들어져야한다.**
   - **windows에서 테스트하기 위해, `rq를 포함하는 models의 Task류 import`는 주석처리하고 테스트한다**
   ```python
    # app/models/__init__.py
    # from .tasks import Task, Notification, Message
    from .sources import Feed, Source, SourceCategory
   ```
   ```python
    if __name__ == '__main__':
        # app/rss_sources/__init__.py
        Base.metadata.create_all(bind=engine)
    
    
        append_markdown = ''
        append_markdown += get_youtube_markdown()
        append_markdown += get_blog_markdown()
        append_markdown += get_url_markdown()
    
        if append_markdown:
            with open('./readme.md', 'w', encoding="UTF-8") as readme:
                with open('./default.md', 'r', encoding="UTF-8") as default:
                    readme.write(default.read()+'\n')
                readme.write(append_markdown)
    
        else:
            parse_logger.info('default readme에 추가할 내용이 없습니다.')
    ```
   
### MarkdownCreator에서 데이터를 받아와 저장하는 부분을 task로 분리하기

#### 정리
- 현재까지 task 정의는 `tasks패키지`내부에서 `.py`모듈을 생성해놓고, `tasks/__init__.py`에
    - 일반 task는 route에서 `TaskService()객체.enqueue_task`( task_func, )로 처리된다
        ```python
        s = TaskService()
        s.enqueue_task
        ```
    - schedule task는 이미 정해진 애들이라 `tasks/init.py에 정의된  def init_app()`에 정의하는데
        - schedule_jobs = [] or cron_jobs = []에 dict로 정의해놓고
        - scheduler_service = SchedulerService()를 통해서 순회하며
        - scheduler_service.exists()로 queue에서 돌고있는지 확인 후 있으면 cancel 후
        - .schedule()로 dict를 집어넣는다.
    ```python
    def init_app(app):
        schedule_jobs = [
            dict(
                scheduled_time=datetime.now(),
                task_func=print, args=['scheduler work...1'], kwargs={},
                description='test',
                interval=timedelta(seconds=30), #repeat=4,
                timeout=timedelta(minutes=10),
            ),
        ]
        cron_jobs = [
            dict(
                cron_string="33 23 * * *",
                task_func=print, args=['cron job 1'], kwargs={},
                description='test',
                timeout=timedelta(minutes=10),
            ),
        ]
        scheduler_service = SchedulerService()
    
        # for job in schedule_jobs:
        for job in schedule_jobs + cron_jobs:
            try:
                existed_schedule = scheduler_service.exists_in_redis(job)
                if existed_schedule:
                    scheduler_service.cancel_schedule(existed_schedule)
    
                if 'scheduled_time' in job:
                    scheduler_service.schedule(
                        **job
                    )
                elif 'cron_string' in job:
                    scheduler_service.cron(
                        **job
                    )
                else:
                    ...
    
            except Exception as e:
                logger.error(f'Schedule register Error: {str(e)}')
    ```

#### model변경 및 필터 개별 구현하기
- firehorse에서는 개별 source마다 run해서 업데이트한다

1. markdown_creator.py에서 이름을 Service로 바꿔서, fetch부분 + get부분만 수정한다
    - target_id는 어차피 환경변수로 처리되기 때문에 생성자에서 안받는다.
        - 원래는 받아서 검증하려고 했지만, get_feeds시에도 내부에서 사용해서, 생성자에서도 내부사용하는 것으로 변경
    - target_id_or_name 부분을 if대신 상속으로 각자 구현
    - displaynumbers도 상속으로 각자구현
    - **filter도 각자 구현**
        - (Youtube, Blog는 Source.target_url에 target_id가 포함) 
            - **Blog의 경우 category에 대한 필터 추가?! like feed parse시 필터링?!**
            - 그러려면, Youtube와 다르게 `target_id + 짝 category`도 애초에 같이 뽑아내야한다
            - 개별로 target_info를 가져오며, 개별 filter를 만든다.
    - Source의 category칼럼은 필요없다. **일단 모든 category를 rss에서 다 취하고, 필터만 주어진 것으로 하자**
      - (URL는 Source.name에 target_name이 포함) 

2. BaseSource의 fetch_feeds()시에는 주어진 category값으로 feed를 필터링 하지 않고, 일단 다 모은다.
    - 나중에 DB에서 get_feed시 필터링 할 생각이다.
    ```python
    class BaseSource:
        def fetch_feeds(self):
    
            total_feeds = []
    
            for url, category in self._url_with_categories:
                result_text = requests_url(url)
                if not result_text:
                    parse_logger.info(f'{self.__class__.__name__}의 url({url})에 대한 request요청에 실패')
                    continue
                feeds = []
                for feed in self.parser.parse(result_text):
                    #### 필터링 -> 취소
                    #### get_feed시 필터링만category를 사용하고, fetch시에는 다 가져온다
                    # if issubclass(self.__class__, TargetSource) and category and not self._is_category(feed, category):
                    #     continue
                    feed = self.map(feed)
                    feed['source'].update(
                        name=self.NAME,
                        url=self.URL,
                        # category=category, # source에는 필터링용 category를 입력하지 않는다.
                    )
    
                    feeds.append(feed)
    
                total_feeds.extend(feeds)
    
            return total_feeds
    ```
   

3. model에서도 Source에서는 category칼럼을 제외시킨다. 오로지 get_feed시 필터링할때만 사용한다
    ```python
    class Source(BaseModel):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.Text, nullable=False)  # 사용자입력 NAME ex> Tistory, Naver, 유튜브, 왓챠
        url = db.Column(db.Text, nullable=False)
        # category = db.Column(db.Text, nullable=True)
        # ...
    ```
    - 테스트 db.sqlite도 삭제해서 새로 생성되게 한다


4. `SourceService` 구) Markdown class의 `get_feeds`메서드에서
    - get_target_id_or_name_list -> 각 SourceCategory마다 필터링에 필요한 정보가 다르므로 `get_target_info_for_filter`로 메서드를 변경하고
    - 각 cls별로 개별 구현하도록 한다
    ```python
    class SourceService:
        #...
        def get_feeds(self):
    
            source_category_name = self.get_source_category_name()
            target_info_for_filter = self.get_target_info_for_filter()
            display_numbers = self.get_display_numbers()
    
            feeds = self._get_feeds(source_category_name, target_info_for_filter, display_numbers)
    
            return feeds
            
        @abstractmethod
        def get_target_info_for_filter(self):
            raise NotImplementedError
    ```
    - Youtube의경우 target_id만 가져와서 필터링한다
    ```python
    class YoutubeService(SourceService):
        def get_target_info_for_filter(self):
            return [target_id for target_id in SourceConfig.youtube_target_ids if target_id]
    
    ```
    - Blog의경우 target_id와 category 모두 가져와서 필터링한다
    ```python
    class BlogService(SourceService):
        def get_target_info_for_filter(self):
    
            return [(target_id, category) for target_id, category in
                    SourceConfig.tistory_target_id_and_categories + SourceConfig.naver_target_id_and_categories
                    if target_id]
    ```
    - URL의경우 target_id와 name 중 name만 가져와서 필터링한다
    ```python
    class URLService(SourceService):
        def get_target_info_for_filter(self):
            return [target_name for target_url, target_name in SourceConfig.url_and_names if target_name]
    ```
 

5. 이제 query를 만들 때, 필요한 정보를 가지고 호출하는데 3가지 정보 중 2가지로 filter를 만든다.
    - 공통적으로 source_category로 `SourceCategory필터링은 공통`이지만, 
    - `Source 및 Feed`에 대한 필터링은 `cls별로 개별 filter`를 만든다.
    ```python
    def get_feeds(self):
        # SourceCategory 필터링
        source_category_name = self.get_source_category_name()
        # Source-target_url(Youtube, Blog) or name(URL) 및 Feed-category(Blog) 필터링
        target_info_for_filter = self.get_target_infos() 
        display_numbers = self.get_display_numbers()

        feeds = self._get_feeds(source_category_name, target_info_for_filter, display_numbers)

        return feeds
    ```
    ```python
    def _get_feeds(self, source_category_name, target_info_for_filter, display_numbers):
        # cls별 개별 필터링 by source_category_name, target_info_for_filter
        filter_clause = self._create_feed_filter_clause(source_category_name, target_info_for_filter)
        
        feeds = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(filter_clause) \
            .order_by(Feed.published.desc()) \
            .limit(display_numbers) \
            .all()
        return feeds
    ```
6. cls별로 filter clause를 작성한다
    - Youtube: Source.target_url이 target_id를 포함하고 있으면 된다.
    ```python
    class YoutubeService(SourceService):
        def get_target_filter_clause(self, target_info_for_filter):
            return or_(*[Source.target_url.contains(target_id) for target_id in target_info_for_filter])
    
    ```
    - Blog: Source.target_url이 target_id를 포함하고, **category가 존재하는 경우, Feed.category와 동일해야한다.**
        - **이 때, 식 자체의 인자가 달라지므로, lambda를 이용해서 호출하게 한다**
    ```python
    class BlogService(SourceService):
        def get_target_filter_clause(self, target_info_for_filter):
            none_category_filter = lambda target_id : Source.target_url.contains(target_id)
            with_category_filter = lambda target_id, category : and_(Source.target_url.contains(target_id), Feed.category == category)
            target_filter = or_(*[none_category_filter(target_id) if not category else with_category_filter(target_id, category) for target_id, category in target_info_for_filter])
            # print(target_info_for_filter)
            # print(target_filter)
            # [('nittaku', 'pythonic practice'), ('is2js', '마왕')]
            # (source.target_url LIKE '%' || :target_url_1 || '%') AND feed.category = :category_1 OR (source.target_url LIKE '%' || :target_url_2 || '%') AND feed.category = :category_2
            return target_filter
    ```
    - URL: Source.name target_name를 포함하고 있으면 된다.
    ```python
    class URLService(SourceService):
    
        def get_target_filter_clause(self, target_info_for_filter):
            return or_(
                *[Source.name.__eq__(target_name) for target_name in target_info_for_filter]
            )
    ```
   
#### Service를 쓰기 전에, Config 수정하기
- 기존에는 id가 없는 경우도, category가 없을 때의 None대입으로 인해  `[(None, None)]`가 진행되었지만
- **id는 데이터가 존재하는 경우만 split -> id_list가 존재할경우에만 category와 list(zip())하고 id가 없다면 `[] 빈리스트`로 반환하게 한다**
    - 그 결과 각 Service들이 id가 없을 경우 raise를 발생시키게 한다
    ```python
    
    class SourceConfig:
        # id는 존재하는 것만 필터링
        tistory_target_ids = [item.strip() for item in os.getenv('TISTORY_TARGET_IDS').split(',') if item]
        # category는 없으면 None으로 채우기
        tistory_categories = [item.strip() if item else None for item in os.getenv('TISTORY_CATEGORIES').split(',')]
        # id가 존재할 때만, None과 함께 longest
        tistory_target_id_and_categories = list(zip_longest(tistory_target_ids, tistory_categories)) if tistory_target_ids else []
    ```
- 기존의 init에서 검사에서 `filter_exist_targets` 구) check_exists 삭제
    ```python
    class BlogService(SourceService):
        def __init__(self):
            sources = []
            # if self.filter_exist_targets(SourceConfig.tistory_target_id_and_categories):
            if SourceConfig.tistory_target_id_and_categories:
                sources.append(Tistory(SourceConfig.tistory_target_id_and_categories))
            if SourceConfig.naver_target_id_and_categories:
                sources.append(Naver(SourceConfig.naver_target_id_and_categories))
    
            if not sources:
                raise ValueError(f'BlogMarkdown에 입력된 target들이 존재하지 않습니다.')
    
            super().__init__(sources)
    ```
  
- 이제 각 Service마다 `Config.tagets`가 존재하지 않으면 바로 에러
    - id가 없으면 `[]`의 빈 list만 들어오니 환경변수 확인해서 에러
    ```python
    class YoutubeService(SourceService):
        def __init__(self):
            if not SourceConfig.youtube_target_ids:
                raise ValueError(f'{self.__class__.__name__}에 대한 환경변수: YOUTUBE_TARGET_IDS가 존재하지 않습니다.')
            super().__init__(Youtube(SourceConfig.youtube_target_ids))
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
    class URLService(SourceService):
    
        def __init__(self):
            if not SourceConfig.url_and_names:
                raise ValueError(f'{self.__class__.__name__}에 대한 환경변수 URL_NAME and URL_LIST 가 존재하지 않습니다.')
    
            sources = [globals()[name](url) for url, name in SourceConfig.url_and_names]
            # if not sources:
            #     raise ValueError(f'URLMarkdown에 입력된 url_and_names들이 존재하지 않습니다.')
            super().__init__(sources)
    ```
  
- 이제 외부에서 try except만 해줘서 각 Service를 호출만 해주면 된다.
    - **환경변수 검사 안해도 내부에서 에러를 내준다.**
#### 테스트용 환경변수(app/rss_sources/.env) -> root의 .env로 옮기기
- 옮기고 나서 model에서 윈도우에러방지 Task모델들을 주석풀어주기

#### tasks에 py모듈(rss_fetcher)로 정의 하고, init_app의 schedule dict에 등록하기
1. tasks패키지에 `rss_fetcher.py`모듈을 만들고, 내부 함수를 정의해준다.
    - **각각을 try/except로 호출하며, 로거는 schedule_logger를 사용해준다.**
    ```python
    # app/tasks/rss_fetcher.py
    from app.rss_sources import YoutubeService, BlogService, URLService, SourceConfig
    from app.utils import schedule_logger
    
    
    def fetch_rss():
        try:
            youtube_service = YoutubeService()
            youtube_updated = youtube_service.fetch_new_feeds()
        except Exception as e:
            schedule_logger.info(f'{str(e)}', exc_info=True)
        try:
            blog_service = BlogService()
            blog_updated = blog_service.fetch_new_feeds()
        except Exception as e:
            schedule_logger.info(f'{str(e)}', exc_info=True)
    
        try:
            url_service = URLService()
            url_updated = url_service.fetch_new_feeds()
        except Exception as e:
            schedule_logger.info(f'{str(e)}', exc_info=True)
    
    ```

2. **팩토리메서드create_app에서 호출되는 `tasks/__init__.py` 속 `def init_app`에서 schedule로 등록해준다**
    - 사용되는 인자가 없다. 내부에서 환경변수 씀.
    - 현재부터 실행되어, 5분마다 호출되게 해준다.
    ```python
    def init_app(app):
        # 지금부터, 몇분 간격으로 (+ 몇번을) 반복해서 실행
        schedule_jobs = [
            dict(
                scheduled_time=datetime.now(),
                task_func=fetch_rss, args=[], kwargs={},
                description='fetch_rss',
                interval=timedelta(minutes=5),
                # repeat=5, # 횟수
                timeout=timedelta(minutes=10),
            ),
        ]
    ```
    
3. `http://localhost:8000/rqschedulerdashboard`에서 등록됨을 확인한다.
    ```
    app.tasks.rss_fetcher.fetch_rss()
    fe87105e-f267-4b69-90d0-f50f18a344ba
    
    18 seconds ago	4 minutes from now	 Cancel
    ```
   

4. db를 보고 제대로 fetch해오는지 확인한다.

5. **주기적 행동이 제대로 작동하면, `cron_job`으로 옮겨준다.**
    - 3시간마다로 넣어준다
    ```python
        cron_jobs = [
    # 3시간마다 rss 패치
            dict(
                cron_string="00 3/ * * *",  # 분|시|(매달)일|월|(매주)요일(1=월요일)
                task_func=fetch_rss, args=[], kwargs={},
                description='fetch_ress',
                timeout=timedelta(minutes=5),
            ),
        ]
    ```
   


#### rss_service -> service패키지로 분리하기
- rss_service에서 base_service로 옮기고
- 각각의 service들을 py모듈로 만든다.
- init에 등록한다
- tasks/rss_fetcher.py에서 사용한다

### github도 똑같이 처음부터 적용하기

### markdown create의 html생성부분을 Service.render()메서드로 옮기기
1. base_serivce.py에 `render`메서드를 정의한다.
    - 각 source_category마다 달라지는 부분을 추상메서드로 구현한다.
        - get_title, set_custom, set_feed_template
        - title_level은 공통상수로서 메서드 기본 keyword에 넣어둔다.
    ```python
    class SourceService:
        def render(self, title_level=SourceConfig.TITLE_LEVEL):
            # updated_at = pytz.timezone('Asia/Seoul').localize(datetime.now())
            # kst로 바로 localize하니까, strftime이 안찍히는 듯
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
   
        @abstractmethod
        def get_title(self):
            raise NotImplementedError
   
        def set_custom(self):
            return ''
    
        @abstractmethod
        def set_feed_template(self, feeds):
            raise NotImplementedError
    ```

2. custom템플릿을 넣거, feed마다 prefix넣는여부를알기 위해 `is_many_source`메서드도 만들어준다.
    - **이 때, 실시간 target정보(id or id+category or name+url)인 `self.get_target_info_for_filter()`를 통해 판단한다**
    - filter에만 사용하는게 아니므로 self.get_target_info_for_filter 를 `get_target_infos`로 변경해주자
    ```python
    def is_many_source(self):
        return len(self.get_target_infos()) > 1
    ```
2. 각 Service마다 `get_title`, `set_custom`, `set_feed_template`를 구현해준다.
    - set_custom 혹은 set_feed_template에서 `self.is_many_source()`가 활용된다.
    ```python
    class YoutubeService(SourceService):
        #...
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
    ```
   
3. blog_service의 경우 is_many_source의 기준을 **Tistory + Naver일때로 둔다**
    ```python
    class BlogService(SourceService):
        def get_title(self):
            return SourceConfig.BLOG_TITLE
    
        def set_custom(self):
            custom_result = ''
    
            return custom_result
    
        def is_many_source(self):
            return len(SourceConfig.tistory_target_id_and_categories) >= 1 and len(SourceConfig.naver_target_id_and_categories) >= 1
    
        def set_feed_template(self, feeds):
            feed_template_result = ''
    
            for feed in feeds:
                feed_text = BLOG_FEED_TEMPLATE.format(
                    feed.url,
                    feed.thumbnail_url,
                    feed.url,
                    feed.title,
                    f'{feed.source.name} | ' if self.is_many_source() else '',
                    feed.published_string
                )
                feed_template_result += feed_text
    
            return feed_template_result
    ```
   
4. url_service
    ```python
    class URLService(SourceService):
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
    ```
   
### github의 경우, manage.py에 service render들을 호출하기 위해 rss_source/init.py에 새로 정의한다
1. rss_source/init.py
    ```python
    def render_all_service(default_path='./default.md', readme_path='./readme.md'):
        youtube_service = YoutubeService()
        blog_service = BlogService()
        url_service = URLService()
    
        markdown_text = ''
        markdown_text += youtube_service.render()
        markdown_text += blog_service.render()
        markdown_text += url_service.render()
    
        with open(readme_path, 'w', encoding="UTF-8") as readme:
            with open(default_path, 'r', encoding="UTF-8") as default:
                readme.write(default.read() + '\n')
            readme.write(markdown_text)
    ```
   
2. manage.py에서 호출한다
    ```python
    from rss_sources import create_database, fetch_all_service, render_all_service
    
    create_database()
    fetch_all_service()
    
    render_all_service()
    ```
   
### init에 SourceConfig를 확인하여, 허용된 Service객체들을 가져오는 메서드 만들기
#### github에서
1. rss_sources/init.py에 `get_current_services`로 현재 사용되는 service객체들을 받아오는 메서드를 만든다.
    ```python
    # rss_sources/__init__.py:
    def get_current_services():
        current_services = []
        if SourceConfig.youtube_target_ids:
            current_services.append(YoutubeService())
        if SourceConfig.tistory_target_id_and_categories or SourceConfig.naver_target_id_and_categories:
            current_services.append(BlogService())
        if SourceConfig.url_and_names:
            current_services.append(URLService())
        return current_services
    ```
2. manage.py에서 `service객체들`을 받아와 `fetch` + `render`를 재활용해서 호출한다
    ```python
    from rss_sources import create_database, get_current_services, parse_logger
    
    # db.sqlite가 없으면 생성
    create_database()
    # 사용지정된 service객체들만 가져오기
    service_list = get_current_services()
    ```
    ```python
    def fetch_feeds_by(service_list):
        for service in service_list:
            try:
                new_feeds = service.fetch_new_feeds()
            except Exception as e:
                parse_logger.info(f'{str(e)}', exc_info=True)
    
    
    def create_readme(service_list):
        markdown_text = ''
        for service in service_list:
            markdown_text += service.render()
    
        with open('./readme.md', 'w', encoding="UTF-8") as readme:
            with open('./default.md', 'r', encoding="UTF-8") as default:
                readme.write(default.read() + '\n')
    
            readme.write(markdown_text)
    
    
    # db.sqlite가 없으면 생성
    create_database()
    # 사용지정된 service객체들만 가져오기
    service_list = get_current_services()
    
    
    fetch_feeds_by(service_list)
    create_readme(service_list)
    ```


### rq프로젝트에서는 service들의 render메서드들을 호출하여 template에 보여줘야한다
1. rss_sources/init에 `get_current_services`를 정의한 뒤
    ```python
    app/rss_sources/__init__.py
    def get_current_services():
        current_services = []
        if SourceConfig.youtube_target_ids:
            current_services.append(YoutubeService())
        if SourceConfig.tistory_target_id_and_categories or SourceConfig.naver_target_id_and_categories:
            current_services.append(BlogService())
        if SourceConfig.url_and_names:
            current_services.append(URLService())
        return current_services
    ```
   

2. tasks/rss_fetcher.py에서 활용하고
    ```python
    # app/tasks/rss_fetcher.py
    from app.rss_sources import get_current_services
    from app.utils import schedule_logger
    
    
    def fetch_rss():
    
        service_list = get_current_services()
        
        for service in service_list:
            try:
                new_feeds = service.fetch_new_feeds()
            except Exception as e:
                schedule_logger.info(f'{str(e)}', exc_info=True)
    ```
   
3. views.py에서도 활용하여, render text를 만든다.
    ```python
    @main_bp.route('/rss', methods=['GET', 'POST'])
    def rss():
        current_services = get_current_services()
    
        markdown_text = ''
        for service in current_services:
            markdown_text += service.render()
   
        return render_template('rss.html', markdown_text=markdown_text)
    ```
   

### markdown text => html로 변환 => jinja | safe필터로 나타내기
1. `markdown2`패키지를 깔고 `markdown2.markdown( markdown_text )`로 변수를 만들어 넘겨줘야한다
    ```shell
    pip install markdown2
    pip freeze > ./requirements.txt
   
    docker-compose build --no-cache app
    ```
   
2. views.py에서 route에 `markdown -> html`변수로 넘겨주기
    ```python
    @main_bp.route('/rss', methods=['GET', 'POST'])
    def rss():
        current_services = get_current_services()
    
        markdown_text = ''
        for service in current_services:
            markdown_text += service.render()
    
        markdown_html = markdown2.markdown(markdown_text)
    
        return render_template('rss.html', markdown_html=markdown_html)
    ```
   
3. rss.html에서 `{{ markdown_html | safe}}`로 찍기
    ```html
        <div>
            {{markdown_html | safe }}
        </div>
    ```