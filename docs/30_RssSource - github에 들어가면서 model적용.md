1. 모델을 적용하려면, BaseSource의 공통 fetch_feeds메서드에서 적용해야할 것 같다.
2. feed데이터를 직접 category로 필터링하고나서 통과된 feed들에 한해
    - category데이터를 있으면 가져오고 없으면 생성해야한다.
    - https://github1s.com/zuobin158/rss_task/blob/master/course.py
    - https://github1s.com/szewczykmira/rss-scraper/blob/master/exchangerate/rates/exchange_rates.py
    - https://github1s.com/gustavosaez/Rss2Telegram/blob/main/rss2telegram.py



### parse -> fetch_feeds 데이터 구조 변경
1. parse()의 source_xxx를 feed의 `source`키에 **객체 형식으로서 dict**로 넣는다.
    - 현재 rss 타겟의 name과 url을 얻을 수 있는상태다.
    ```python
    # rss_sources/parser.py
    class RssParser(object):
        def parse(self, text):
            for entry in feed.entries:
    
                data = dict()
                # data['source_name'] = source.get('title', None)
                # data['source_url'] = source.get('link', None)
                data['source'] = dict(
                    target_name=source.get('title', None),
                    target_url=source.get('link', None)
                )
    ```
   

#### fetch_feeds시 개별feed 처리는 db와 상관없는 영역이라 치고, source의 사용자 입력 name, url(NAME, URL)만 추가 입력해준다
1. target_name, target_url을 채운 feed['source'] dict에 `update`를 통해 추가로 채운다
    - 카테고리도 source에 넣어준다.
```python
class BaseSource:
    def fetch_feeds(self):

        total_feeds = []
        for url, category in self._url_with_categories:
            result_text = requests_url(url)

            # [FAIL] 요청 실패시 넘어가기
            if not result_text:
                parse_logger.info(f'{self.__class__.__name__}의 url({url})에 대한 request요청에 실패')
                continue
            # [SUCCESS] 요청 성공시 parse(generate)로 feed dict 1개씩 받아 처리하기
            feeds = []
            for feed in self.parser.parse(result_text):
                if issubclass(self.__class__, TargetSource) and category and not self._is_category(feed, category):
                    continue
                feed = self.map(feed)
                
                feed['source'].update(
                    name=self.NAME,
                    url=self.URL,
                    category=category,
                )
```
### SourceCategory정보 및  DB적용은 BaseSource 바깥, 각 Markdown에서 채워야한다
- 나중에 Markdown은 DB로부터만 받아서 그리고 **각 category별 `Service`를 따로 내어야한다**

1. category필터링된 feed를 sources -> source 순회하면서 `source cls`기반으로 sourceCategory객체를 만들어, `source` dict의 관계key `source_category`객체로 넣어 만든다.
    - 이후 `source` dict를 분배하여 `Source`객체를 생성한다.
    - feed dict가 관계객체까지 다 완성되었으니 분배하여 `Feed`객체를 만든다.
    - 이 때, **feed의 `url`로 먼저 찾아 `중복 Feed`면, 필터링되어야하지만, `title=이 다르게 들어온 경우는, 전체를 업뎃`해준다**
    ```python
    class Markdown:
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            markdown_text = ''
    
            feeds = []
    
            for source in self.sources:
                # request 작업
                fetch_feeds = source.fetch_feeds()
                # DB 작업
                for feed in fetch_feeds:
                    # 0) db로의 처리를 위해 sourcecategory / source / feed 형태 잡아주기
                    # - SourceCategory정보를 feed['source']내부 source_category 객체로 만들어주기 ( 임시 )
                    feed['source']['source_category'] = SourceCategory.get_or_create(
                        name=self.__class__.__name__.replace('Markdown', '')
                    )
                    # - source dict를 Source객체로 바꿔주기
                    feed['source'] = Source.get_or_create(**feed['source'])
    
                    # 1) url로 필터링 + title이 달라질 경우는 update
                    prev_feed = Feed.query.filter_by(url=feed['url']).first()
                    if prev_feed:
                        if feed['title'] != prev_feed.title:
                            print(feed, "url존재하지만 title이 수정되어 변경만")
                            prev_feed.update(**feed)
                        continue
    
                    feeds.append(Feed(**feed))
    ```

2. 이 때, **feed의 부모인 Source, 그것의 부모인 SourceCategory는 `이미 생성될 가능성 + 1번만 생성`하면 되므로 `get_or_create`메서드가 필요하다**
    - 기본적으로 `생성할 가능성`이 있으니 `dict -> 전체keyword`를 다 입력받아야한다.
    - **기본적으로 받은 전체keyword로 find -> get하도록 basemodel에 정의한다**
    ```python
    class BaseModel(Base):
        __abstract__ = True
        @classmethod
        def get_or_create(cls, **kwargs):
            instance = cls.query.filter_by(**kwargs).first()
            if instance is None:
                instance = cls(**kwargs)
                instance.save()
    
            return instance
    
    ```
3. **SourceCategory는 name으로 find, Source는 url로 find해서 중복인지 확인한다.**
    - SourceCategory는 name이 전체 keyword므로 수정할 필요없다
    - Source는 `target_url`만으로 찾아야한다.
        - **source의 url은 사용자입력 공통 url이고, target_url이 source안의  여러 target_id에 대한 여러 target_url이며 중복 대상으로 지정된다.**
    - **keyword `get_key=`를 인자로 받아 `주어지는 경우에는 특정칼럼으로만 get을 검색`한다**
    ```python
    class BaseModel(Base):
        @classmethod
        def get_or_create(cls, get_key=None, **kwargs):
            if not get_key:
                instance = cls.query.filter_by(**kwargs).first()
            else:
                instance = cls.query.filter(getattr(cls, get_key) == kwargs.get(get_key)).first()
            if instance is None:
                instance = cls(**kwargs)
                instance.save()
    
            return instance
    ```
    - Source는 get의 기준을 `target_url=`로 찾아서, 없으면 생성한다. 같은 youtube라도, target_id -> target_url에 따라 다른 source가 되게 한다
    ```python
    for feed in fetch_feeds:
        feed['source']['source_category'] = SourceCategory.get_or_create(
            name=self.__class__.__name__.replace('Markdown', '')
            )
        # - source dict를 Source객체로 바꿔주기 + url로만 존재여부 판단하기
        feed['source'] = Source.get_or_create(**feed['source'], get_key='target_url')
    ```

4. 중복시 업데이트되는 feed말고 new_feed에 대해서 `add_all`로 bulk_insert한다
    ```python
    class Markdown:
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            markdown_text = ''
    
            feeds = []
    
            for source in self.sources:
                # request 작업
                fetch_feeds = source.fetch_feeds()
                # DB 작업
                for feed in fetch_feeds:
                    feed['source']['source_category'] = SourceCategory.get_or_create(
                        name=self.__class__.__name__.replace('Markdown', '')
                    )
                    feed['source'] = Source.get_or_create(**feed['source'], get_key='target_url')
                    prev_feed = Feed.query.filter_by(url=feed['url']).first()
                    if prev_feed:
                        if feed['title'] != prev_feed.title:
                            print(feed, "url존재하지만 title이 수정되어 변경만")
                            prev_feed.update(**feed)
                        continue
    
                    feeds.append(Feed(**feed))
            if not feeds:
                parse_logger.info(f'{self.__class__.__name__}에서 feed가 하나도 없어 Markdown 생성이 안되었습니다.')
                return markdown_text
    
            session.add_all(feeds)
            session.commit()
    ```

