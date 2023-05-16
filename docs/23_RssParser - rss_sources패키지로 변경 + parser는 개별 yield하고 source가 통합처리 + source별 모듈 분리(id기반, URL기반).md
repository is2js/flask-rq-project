### 참고
- https://vscode.dev/github/wybiral/firehose/blob/master/parsers/rss/__init__.py
```python
Tistory	https://hyune-c.tistory.com/rss
네이버2: url = 'https://rss.blog.naver.com/{아이디}.xml'
Github  https://{아이디}.github.io/feed.xml


유튜브1:https://www.youtube.com/feeds/videos.xml?channel_id=(채널 ID)
유튜브3: https://www.youtube.com/feeds/videos.xml?playlist_id=(플레이리스트 ID)
유튜브 썸네일1: https://img.youtube.com/vi/%7B%EC%95%84%EC%9D%B4%EB%94%94%7D/maxresdefault.jpg
유튜브 썸네일2: https://img.youtube.com/vi/%7B%EC%95%84%EC%9D%B4%EB%94%94%7D/hqdefault.jpg

Medium	https://medium.com/feed/@{아이디}
Brunch	프로필에서 '페이지 소스 보기' 후 RSS 검색

디스코드봇 활용법: https://discordbot.tistory.com/7
```
#### table을 이용한 카드 마크다운예시
<!-- YOUTUBE:START --><table><tr><td><a href="https://www.youtube.com/watch?v=fj73bxmP03g"><img width="140px" src="https://i.ytimg.com/vi/fj73bxmP03g/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=fj73bxmP03g">നിങ്ങൾ ഒരു വിദ്യാർത്ഥിയാണെങ്കിൽ ഇതിനെക്കുറിച്ച് അറിയു - Microsoft Learn Student Ambassadors Program</a><br/>Feb 11, 2023</td></tr></table>
<table><tr><td><a href="https://www.youtube.com/watch?v=qOckacF3WJo"><img width="140px" src="https://i.ytimg.com/vi/qOckacF3WJo/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=qOckacF3WJo">[Selected] GitHub Campus Experts Application Video | Feb 2022 | Kerala</a><br/>Aug 6, 2022</td></tr></table>
<table><tr><td><a href="https://www.youtube.com/watch?v=EXDn6uWs254"><img width="140px" src="https://i.ytimg.com/vi/EXDn6uWs254/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=EXDn6uWs254">&lpar;+1 Computer Science&rpar; Discipline of Computing #7 - Generations of Computer Pt.3 | Kerala Syllabus</a><br/>Nov 24, 2021</td></tr></table>
<table><tr><td><a href="https://www.youtube.com/watch?v=-HwTYq1BL50"><img width="140px" src="https://i.ytimg.com/vi/-HwTYq1BL50/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=-HwTYq1BL50">&lpar;+1 Computer Science&rpar; Discipline of Computing #6 - Generations of Computer Pt.2 | Kerala Syllabus</a><br/>Nov 14, 2021</td></tr></table>
<table><tr><td><a href="https://www.youtube.com/watch?v=GFsyBBRKOqE"><img width="140px" src="https://i.ytimg.com/vi/GFsyBBRKOqE/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=GFsyBBRKOqE">&lpar;+1 Computer Science&rpar; Discipline of Computing #5 - Generations of Computer  Pt.1 | Malayalam</a><br/>Nov 11, 2021</td></tr></table>
<!-- YOUTUBE:END -->



### 시작
#### for순회를 위에서 빈list에서 모으지말고, for내부에서 dict로 모아 yield로 1개씩 방출 -> 바깥에서 iter(for의 in)으로 쓴다
1. `for 내부`에서 print 하던 것들을 `yield`로 하나씩 방출한다.
    - utc_published는 `published`로 -> DB저장 및 필터링용 
      - kst_published + strftime은 `published_string`로 -> 출력용
          - 각각 따로 저장해서 yield해준다.
      - **entry에 id가 있으면 id로, 없으면 url을 id로 넣어준다.**
    ```python
    def parse(self):
        result_text = requests_url(self.headers, self.target_id, self._url)
        if not result_text:
            return False
    
        feed = feedparser.parse(result_text)
    
        total_count = len(feed.entries)
        if total_count == 0:
            parse_logger.error(f'{self.__class__.__name__}의 target_id({self.target_id})에 feed들이 하나도 존재 하지 않습니다.')
            return False
        source = feed['feed']
        self._source_url = source.get('link', None)
        print(f"출저 url: {self._source_url}")
        print(f"출저 제목: {source.get('title', None)}")
        print(f"출저 부제목: {source.get('subtitle', None)}")
        print(f'총 글 갯수: {total_count}')
        for entry in feed.entries:
            # print('==============')
            # 1개씩 for문내부에서 만든 dict를 yield하여 부모에게 방출
            data = dict()
            # url이 uniquekey라서 id로 삽입할 예정인데, id가 있다면 id로 넣고 없으면 url로 넣자
            #if 'id' in entry:
            #    data['id'] = entry['id']
            #else:
            #    data['id'] = entry.get('link')
    
            # print(f'링크: {entry.get("link")}')
            data['url'] = entry.get("link")
    
            # print(f'카테고리: {_get_category(entry.get("tags"))}')
            data['category'] = _get_category(entry.get("tags"))
    
            # print(f'제목: {_get_text_title(entry.get("title"))}')
            data['title'] = _get_text_title(entry.get("title"))
    
            # if thumbnail:
            #     thumb_count += 1
            # print(f'thumbnail : {thumbnail}')
            thumbnail = _get_thumbnail(entry) or self._get_og_image_url() or \
                        self._get_naver_post_image_url(entry.get("link"))
            data['thumbnail_url'] = thumbnail
            # print(f'내용: {_get_text_body(entry)}')
            data['body'] = _get_text_body(entry)
    
            # 날짜: 2019-02-21 02:18:24
            # 1) published_parsed + mktime + fromtimestamp + pytz
            # utc_published = time_struct_to_utc_datetime(entry.get("published_parsed"))
    
            # 2) published + datetutil + pytz
            utc_published = parser.parse(entry.get('published'))
            # print("published + dateutil.parser", utc_published, type(utc_published))
            data['published'] = utc_published
    
            # 출력용
            kst_published = utc_to_local(utc_published)
            # print(f'날짜: {kst_published.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")}')
            data['published_string'] = kst_published.strftime("%Y년 %m월 %d일 %H시 %M분 %S초") # .strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
    
            yield data
    ```
   
2. main에서 방출메서드 parse(generator)를 `for in`에서 사용하여 하나씩 출력해본다.
    - **추후 Source cls내부에서 self.parser를 가지고, 호출할 것이다.**
```python
if __name__ == '__main__':
    youtube_parser = YoutubeParser('UChZt76JR2Fed1EQ_Ql2W_cw') # 재성
    for feed in youtube_parser.parse():
        print(feed)


{
 'url': 'https://www.youtube.com/watch?v=jlUAviuAuGk', 
 'category': None, 
 'title': 'python widget으로 만든 진료보조 드로잉 노트입니다.', 
 'thumbnail_url': 'https://i3.ytimg.com/vi/jlUAviuAuGk/hqdefault.jpg', 
 'body': 'python widget으로 몸의 구조별 이미지를 선택한 뒤, 드로잉을 통해 환자들에게 질환의 예후 등을 설명할 수 있습니다.\n\nhttps://github.com/is2js/KoreanMedicineNote', 
 'published': datetime.datetime(2021, 10, 27, 13, 53, 17, tzinfo=tzutc()), 
 'published_string': '2021년 10월 27일 22시 53분 17초'
}
```
### parser는 http요청없이 rss만 파싱하고, url과 request는 외부 Source클래스에서 하자.
- 참고: https://vscode.dev/github/wybiral/firehose/blob/master/parsers/rss/__init__.py
1. 각 BaseParser을 상속하던 TistoryParser, NvaerPaser, YoutubeParser의 parse()내용이 같으므로
    - BaseParser -> RssParser로 이름을 변경한다.
    - 각 SourceParser들은 _url만 바뀌게 처리되므로 삭제되고 각 Source들로 바뀔 예정
    ```python
    class RssParser(object):
        def __init__(self, target_id):
            self.target_id = target_id
    ```
2. `BaseSource`는 공통 각 Source들마다, 1개가 아닌 여러 `target_id`(source_url) list를 가지고 있도록 설계한다.
    - **각 Source마다 `상속한 cls를 생성 예정`이므로 생성자에서 안받아도되는 `cls 상수로 처리`하게 한다**
    - **각 Source마다 target_id -> url로 바꾸는 과정이 다르니, 상속cls에서 처리하게 한다**
    - `source.py`를 만들고 BaseSource를 정의한다.
    - **target_ids list를 확정하고, `각 Source마다 다른 url생성방식을 각각 구현할 예정`이다.**

    ```python
    class BaseSource:
        NAME = ''  # source 이름
        URL = ''  # source 자체 url (not rss)
    
        def __init__(self, target_ids):
            self._urls = self._generate_urls(self.check_list(target_ids))
    
        @staticmethod
        def check_list(target_ids):
            if not isinstance(target_ids, (list, tuple, set)):
                target_ids = [target_ids]
            return target_ids
    
        def _generate_urls(self, target_ids):
            raise NotImplementedError
    ```
   

3. 각 Source cls마다 `_generate_urls`를 정의해서 확인해본다.
    ```python
    class Tistory(BaseSource):
        NAME = '티스토리'
        URL = 'https://www.tistory.com/'
    
        def _generate_urls(self, target_ids):
            return list(map(lambda target_id: f"https://{target_id}.tistory.com/rss", target_ids))
    
    
    class Naver(BaseSource):
        NAME = '네이버'
        URL = 'https://www.naver.com/'
    
        def _generate_urls(self, target_ids):
            return list(map(lambda target_id: f"https://rss.blog.naver.com/{target_id}.xml", target_ids))
    
    
    class Youtube(BaseSource):
        NAME = '유튜브'
        URL = 'https://www.youtube.com/'
    
        def _generate_urls(self, target_ids):
            return list(map(lambda target_id: self._build_youtube_url(target_id), target_ids))
    
        @staticmethod
        def _build_youtube_url(target_id):
            BASE_URL = 'https://www.youtube.com/feeds/videos.xml?'
            if target_id.startswith("UC"):
                return BASE_URL + '&' + 'channel_id' + '=' + target_id
            elif target_id.startswith("PL"):
                return BASE_URL + '&' + 'playlist_id' + '=' + target_id
            else:
                raise ValueError(f'UC 또는 PL로 시작해야합니다. Unvalid target_id: {target_id}')
    if __name__ == '__main__':
        print(Tistory('nittaku')._urls)
        print(Naver('is2js')._urls)
        print(Youtube('UChZt76JR2Fed1EQ_Ql2W_cw')._urls)
    # ['https://nittaku.tistory.com/rss']
    # ['https://rss.blog.naver.com/is2js.xml']
    # ['https://www.youtube.com/feeds/videos.xml?&channel_id=UChZt76JR2Fed1EQ_Ql2W_cw']
    ```
   
### Paser구조 변경
- 각각의 Source클래스들이 url들을 순회하면서, parser로 처리해야하는데, **`parser.parse(target_id)`부터 바꿔야한다.**
- **`Parse cls 생성자에 target_id넣는 것`을 삭제하고 바로 생성해서 BaseSource로 들어가게 한다.**
- **RssParser의 requests부분을 Source로 빼야한다.**

1. RssParser의 생성자에 받던 target_id를 삭제하고, `requests_url메서드`는 Parser, Source 둘다 사용되므로 따로 util로 뺀다.
    ```python
    class RssParser(object):
        # def __init__(self, target_id):
        def __init__(self):
            # self.target_id = target_id
            # self._url = None
            # self.headers = {
            #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
            # }
    ```
2. rss_parser/utils.py를 만든다.
    ```python
    # app/rss_parser/utils.py
    
    import requests
    
    from app.utils import parse_logger
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
    }
    
    def requests_url(url, params=None):
        response = requests.get(url, headers=headers, params=params, timeout=3)
        try:
            # if response.status_code != 200:
            #     raise requests.HTTPError
            response.raise_for_status()  # Raises :class:`HTTPError`, if one occurred.
            return response.text
        except requests.exceptions.ReadTimeout:
            parse_logger.error(f'[ReadTimeout] requests 요청 실패( url: {url})')
        except requests.HTTPError:
            parse_logger.error(f'[HTTPError] requests 요청 실패( url: {url})')
        return False
    ```
   

2. Rssparser의 parse()메서드는 target_id가 아닌 reqeust -> .text -> `text`만 받으면 된다.
    ```python
    def parse(self, text):
        feed = feedparser.parse(text)
    ```

### Source에서 urls들을 돌면서 reqeuest_url + 하여 parse(url)까지 호출하기
1. BaseSource에, RssParser객체를 `self.parser`에서 소유한 뒤, 자신이 가진 `self._urls`를 순회하며 request하는 메서드 **`fetch_feed`(피드 가져오기)**를 생성한다
    ```python
    from app.rss_parser.parser import RssParser
    
    class BaseSource:
        NAME = ''  # source 이름
        URL = ''  # source 자체 url (not rss)
    
        def __init__(self, target_ids):
            self._urls = self._generate_urls(self.check_list(target_ids))
            self.parser = RssParser()
    ```
2. **각 Source들이 self._urls를 순회하여 reqeust -> 성공시 parser하는 `fetch_feeds`메서드를 구현한다**
    ```python
    class BaseSource:
        NAME = ''  # source 이름
        URL = ''  # source 자체 url (not rss)
    
        def __init__(self, target_ids):
            self._urls = self._generate_urls(self.check_type(target_ids))
            self.parser = RssParser()
             
        #...
        
        def fetch_feeds(self):
    
            total_feeds = []
    
            for url in self._urls:
                result_text = requests_url(url)
                # [FAIL] 요청 실패시 넘어가기
                if not result_text:
                    parse_logger.info(f'{self.__class__.__name__}의 url({url})에 대한 request요청에 실패')
                    continue
    
                feeds = []
                # [SUCCESS] 요청 성공시 parse(generate)로 feed dict 1개씩 받아 처리하기
                for feed in self.parser.parse(result_text):
                    # [추가삽입] 부모인 source정보 삽입 -> DB적용시 source의 id로 대체?!
                    feed['source_category_name'] = self.NAME
                    feed['source_category_url'] = self.URL
    
                    feeds.append(feed)
    
                total_feeds.extend(feeds)
    
            return total_feeds
    ```

    ```python
    if __name__ == '__main__':
        naver = Naver('is2js')
        pprint(naver.fetch_feeds())
        # [
        #  {
        #   'body': '222asdfsdfasdf333asdfaasdfasdfasdfasa',
        #   'category': '마왕',
        #   'published': datetime.datetime(2023, 5, 10, 18, 33, 11, tzinfo=tzoffset(None, 32400)),
        #   'published_string': '2023년 05월 10일 18시 33분 11초',
        #   'source_category_name': '네이버',
        #   'source_category_url': 'https://www.naver.com/',
        #   'thumbnail_url': None,
        #   'title': 'ddd',
        #   'url': 'https://blog.naver.com/is2js/223098522367'
        #   },
        # ]
    ```
   
3. 기존의 각 SoureParser cls들은 삭제한다.

### target_id(tistory, naver, youtube -> url만들기)가 없이 RSS_url만 들고 있는 경우 처리
- **BaseSource에 `_generate_urls`의 구현은 반드시 해야한다. `직접 url를 입력하는 BaseSource`를 만들자**
    - **id를 받는 tistroy, naver, youtube는 `TargetgSource`로 만들고, 공통 부분만 새로 BaseSource를 만들자.**
    - **즉, `URLSource`도 만들어, 공통메서드 (`check_type`, `fetch_feeds`)를 소유하면서, `생성자에서 urls list`를 직접 받아 넣도록 하자.**

1. BaseSource 새로 정의
    ```python
    class BaseSource:
        NAME = ''  # source 이름
        URL = ''  # source 자체 url (not rss)
    
        def __init__(self):
            self._urls = None
            self.parser = RssParser()
    
        @staticmethod
        def check_type(target_ids_or_urls):
            if not isinstance(target_ids_or_urls, (list, tuple, set)):
                target_ids_or_urls = [target_ids_or_urls]
            return target_ids_or_urls
        def fetch_feeds(self):
    
            total_feeds = []
    
            for url in self._urls:
                result_text = requests_url(url)
                # [FAIL] 요청 실패시 넘어가기
                if not result_text:
                    parse_logger.info(f'{self.__class__.__name__}의 url({url})에 대한 request요청에 실패')
                    continue
    
                feeds = []
                # [SUCCESS] 요청 성공시 parse(generate)로 feed dict 1개씩 받아 처리하기
                for feed in self.parser.parse(result_text):
                    # [추가삽입] 부모인 source정보 삽입 -> DB적용시 source의 id로 대체?!
                    feed['source_category_name'] = self.NAME
                    feed['source_category_url'] = self.URL
    
                    feeds.append(feed)
    
                total_feeds.extend(feeds)
    
            return total_feeds
    ```
   
2. **입력타입에 따라 `TargetSource`와 `URLSource`로 추가 Base cls를 만들고, `서로 다른 방식으로 self._urls`를 만든다.**
    ```python
    class URLSource(BaseSource):
        def __init__(self, urls):
            super().__init__()
            self._urls = self.check_type(urls)
    
    
    class TargetSource(BaseSource):
        def __init__(self, target_ids):
            super().__init__()
            self._urls = self._generate_urls(self.check_type(target_ids))
    
        def _generate_urls(self, target_ids):
            raise NotImplementedError
    ```
   
3. `URLSource기반`의 cls를 생성한다. NAME+URL 상수 및 `target_id + generate_urls`가 아닌 **`urls`를 직접입력하여 내부 self._urls를 만든다.**
    - **필수 구현인 _generate_urls를 구현안하고 직접 rss url을 입력한다.**
    ```python
    class 민족의학신문(URLSource):
        NAME = '민족의학신문'
        URL = 'https://www.mjmedi.com//'
    ```
    ```python
    if __name__ == '__main__':
        pprint(민족의학신문('http://www.mjmedi.com/rss/clickTop.xml').fetch_feeds())
        # [{'body': '[민족의학신문=김춘호 기자] 건강보험심사평가원 서울지원(지원장 지점분, 이하 서울지원)은 10일 서울 동작구 소재 '
        #           '굿네이버스 서인지역본부(본부장 홍선교)를 방문해 어린이 놀이키트를 전달했다고 밝혔다.이번 나눔행사는 심사평가원이 실시한 '
        #           '임직원 ESG 실천 프로젝트 ‘HIRA人 한마음 워킹챌린지 부서대항전’에서 서울지원을 포함한 부산지원과 의료급여실이 각 '
        #           '조별 우승팀으로 선정되어 지역사회에 물품을 후원할 기회가 주어졌다. 이에 서울지원은 아동양육시설 어린이들을 위한 놀이키트 '
        #           '6세트를 후원했고, 해당 키트는 보육원 6곳에 각각 비치 될',
        #   'category': None,
        #   'published': datetime.datetime(2023, 5, 10, 16, 29, 45),
        #   'published_string': '2023년 05월 10일 16시 29분 45초',
        #   'source_category_name': '민족의학신문',
        #   'source_category_url': 'https://www.mjmedi.com//',
        #   'thumbnail_url': None,
        #   'title': '심평원 서울지원, 걷기 활동 나눔행사 실시',
        #   'url': 'http://www.mjmedi.com/news/articleView.html?idxno=56571'},
    ```
   

### TargetSource와 URLSource를 패키지로 분리
1. rss_parser 대신 -> `rss_sources` 패키지를 만들고, 기존 source.py -> `base_source.py`로 변경한다.
2. 각각의 구현Source cls를 각 부모source class명에 따라 `py모듈`로 각각 옮긴다.
    - **이 때, 각 하위모듈에서 `상위의 base_source.py`는 상위 init에 안올라가기 때문에, `풀경로로 import`해도 된다.**
    - class Tistory(TargetSource) -> `targets/tistory.py`
    ```python
    from app.rss_sources.base_source import TargetSource
    
    
    class Tistory(TargetSource):
        NAME = '티스토리'
        URL = 'https://www.tistory.com/'
    
        def _generate_urls(self, target_ids):
            return list(map(lambda target_id: f"https://{target_id}.tistory.com/rss", target_ids))
    ```
    - class 민족의학신문(URLSource) -> `urls/민족의학.py`
    ```python
    from app.rss_sources.base_source import URLSource

    class 민족의학신문(URLSource):
        NAME = '민족의학신문'
        URL = 'https://www.mjmedi.com/'
    ```
    ![img.png](images\source_package.png)

3. 각 하위모듈별 init.py에 .import로 cls들을 모은다
    ```python
    # app/rss_sources/targets/__init__.py
    from .naver import Naver
    from .tistory import Tistory
    from .youtube import Youtube
    
    # app/sources/urls/__init__.py
    from .민족의학신문 import 민족의학신문
    ```
4. 구현된 모듈은 sources/init.py에 `from targets import *` `from urls import *`로 다 모이게 한다.
    ```python
    # app/rss_sources/__init__.py
    from targets import *
    from urls import *
    ```

5. sources/init.py에서 main을 만들어 테스트한다.
    ```python
    # app/rss_sources/__init__.py
    from .targets import *
    from .urls import *
    
    if __name__ == '__main__':
        from pprint import pprint
        tistory = Tistory('nittaku')
        pprint(tistory.fetch_feeds())
    ```

#### 각각의 Source를 만드는 방법
1. **target_id**를 입력받는 경우, `sources/targets`폴더에**
    1. rss target id를 받아오는 출저 이름으로 py모듈을 만든다. ex> tistory.py
    2. `TargetSource`를 상속하는 출저cls를 만들고, `NAME, URL` 상수를 기입한다.
    3. **필수적으로 `target_ids를` 받는 `_generate_urls`를 구현하며, 내부에서 target_id -> rss_url로 바꾸는 로직을 구현한다.**
        ```python
        from app.rss_sources.base_source import TargetSource
        class Tistory(TargetSource):
            NAME = '티스토리'
            URL = 'https://www.tistory.com/'
        
            def _generate_urls(self, target_ids):
                return list(map(lambda target_id: f"https://{target_id}.tistory.com/rss", target_ids))
        ```
    4. targets/init.py에 cls를 .import한다
    5. **해당모듈을 사용할 때, `target_id or target_id list를 생성자에 입력`한다**
        ```python
        from app.rss_sources import Tistory
        pprint(Tistory('nittaku').fetch_feeds())
        ```
2. **rss_url을 받는 경우, `sources/urls`폴더에**
    1. py모듈을 만들고 ex> 민족의학신문.py
    2. `URLsource`를 상속하는 출저cls를 만들고, `NAME, URL`상수를 기입한다.
    3. **딱히 구현해야할 메서드는 없다.**
        ```python
        from app.rss_sources.base_source import URLSource
        class 민족의학신문(URLSource):
            NAME = '민족의학신문'
            URL = 'https://www.mjmedi.com/'
        ```
    4. urls/init.py에 cls를 .import한다
    5. **해당모듈을 사용할 때, `rss_url or rss_url list를 생성자에 입력`한다**
        ```python
        from app.rss_sources import 민족의학신문
            
        pprint(민족의학신문('http://www.mjmedi.com/rss/clickTop.xml').fetch_feeds())
        ```

