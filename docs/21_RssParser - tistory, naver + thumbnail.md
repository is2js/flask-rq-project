- 참고: 멀티URL + 파싱 https://waylonwalker.com/parsing-rss-python/
- 참고1: Source + Article + Youtbe튜토리얼 : https://github.com/code-tutorials/python-feedreader/blob/master/models/source.py
  - 유튜브: https://www.youtube.com/watch?v=0eEJC4NwoqU&list=PLmxT2pVYo5LBcv5nYKTIn-fblphtD_OJO&index=11
- 참고2: fastapi버전 + bs4 이미지파싱까지: https://github.com/wybiral/firehose/blob/master/parsers/rss/__init__.py

```python
Tistory	https://hyune-c.tistory.com/rss
네이버2: url = 'https://rss.blog.naver.com/{아이디}.xml'
Github  https://{아이디}.github.io/feed.xml


유튜브1:https://www.youtube.com/feeds/videos.xml?channel_id=(채널 ID)
유튜브2:https://www.youtube.com/feeds/videos.xml?user=(유저명)
유튜브3: https://www.youtube.com/feeds/videos.xml?playlist_id=(플레이리스트 ID)
유튜브 썸네일1: https://img.youtube.com/vi/%7B%EC%95%84%EC%9D%B4%EB%94%94%7D/maxresdefault.jpg
유튜브 썸네일2: https://img.youtube.com/vi/%7B%EC%95%84%EC%9D%B4%EB%94%94%7D/hqdefault.jpg

Medium	https://medium.com/feed/@{아이디}
Brunch	프로필에서 '페이지 소스 보기' 후 RSS 검색

디스코드봇 활용법: https://discordbot.tistory.com/7
```

### Tistory, Naver RSS(xml) 기본 파싱기
1. feedparser, bs4 설치

2. blog_parser 패키지를 만들고, `service.py`를 생성한 뒤
    - BaseParser, TistoryParser, NaverParser를 구현한다
    - **각 블로그들은 `공통`으로 url 속 `target_id`를 받는다.**
    - **`url`은 target_id에 따라 서로 다른 모양을 해서 각각으로 받을 예정이었지만, parse메서드가 blog는 공통으로 사용될거라 `self.__url=None`으로 초기화만 해준다**
    - 이 때, __url로 지으면 상속으로 덮어쓰기도 안된다. _url로 지음
    ```python
    class BaseParser(object):
        def __init__(self, target_id):
            self.target_id = target_id
            self._url = None # 공통 parse함수를 위해                              
    ```
   


3. parse는 tistory, naver 둘다 공통이더라
   - `feedparser.parse(self._url)`의 결과를 `feed`로 본다면, `.status`에서 200이 아니거나 `파싱할 글 갯수`가 없으면, return False한다
   - feed.feed는 **블로그 전반의 정보 `source`를 담고 있다.**
      - 여기선 `generator`: 발행 블로그 종류, `link`: 블로그 주소, `title`: 제목, `subtitle`: 부제목 or 자기소개를 가져온다
   - feed.entries에는 **각 피드아이템들을 `최대 50개`까지 들고 있다. 티스토리의 경우, 50개까지 늘리는 설정이 있다.**
      - 블로그 카테고리는 `tags`가 있을 경우, list로 반환되며, 거기서 `term`을 찾아야한다. 
         - tags가 없거나 or term이 없는 경우 `None`으로 반환
      - `title` : 제목
      - `summary` : 내용(body)
      - `link` : 해당글 url
      - `published_parsed` : date가 time.struct 타입으로 되어있는데, 
         - **`time.mktime()`을 이용해 seconds로 변경하고** 
         - **`datetime.fromtimestamp()`을 이용해 seconds를 datetime으로 변경한다**
         - 없는 경우도 있으니, if문을 달아서 없으면 None
   ```python
   class BaseParser(object):
       def __init__(self, target_id):
           self.target_id = target_id
           self._url = None # 공통 parse함수를 위해
   
       def parse(self):
           feed = feedparser.parse(self._url)
   
           if feed.status != 200:
               return False
   
           total_count = len(feed.entries)
           if total_count == 0:
               return False
           print('------------')
           source = feed['feed']
           print(f"출저 타입: {source['generator']}")
           print(f"출저 url: {source['link']}")
           print(f"출저 제목: {source['title']}")
           print(f"출저 부제목: {source['subtitle']}")
           print(f'총 글 갯수: {total_count}')
           for entry in feed.entries:
               # pprint(feed.keys())
               # dict_keys(['title', 'title_detail', 'links', 'link', 'summary', 'summary_detail', 'tags', 'authors', 'author', 'author_detail', 'id', 'guidislink', 'comments', 'published', 'published_parsed'])
   
               # None or [{'term': 'pythonic practice', 'scheme': None, 'label': None}]
               print('==============')
               print(f'카테고리: {_get_category(entry.get("tags"))}')
               print(f'제목: {entry.get("title")}')
               print(f'내용: {entry.get("summary")}')
               print(f'링크: {entry.get("link")}')
               # 날짜: 2019-02-21 02:18:24
               print(f'날짜: {_struct_to_datetime(entry.get("published_parsed"))}')
               break
   
           return feed
   ```
   ```python
    def _get_category(tags):
        if tags:
            return tags[0].get("term", None)
        return None
    
    
    def _struct_to_datetime(published_parsed):
        if not published_parsed:
            return None
    
        from datetime import datetime
        from time import mktime
    
        # mktime -> seconds로 바꿔줌 +  fromtimestamp -> seconds를 datetime으로 바꿔줌
        return datetime.fromtimestamp(mktime(published_parsed))
    ```
   
4. TistoryParser를 만들고, main에서 실험한다
    ```python
    class TistoryParser(BaseParser):
        def __init__(self, target_id):
            super().__init__(target_id)
            self._url = f"https://{self.target_id}.tistory.com/rss"
    ```
    ```python
    if __name__ == '__main__':
        tistory_parser = TistoryParser('nittaku')
        tistory_parser.parse()
    ```
    ```
    # ------------
    출저 타입: TISTORY
    출저 url: https://nittaku.tistory.com/
    출저 제목: 동신한의 조재성 - 머신러닝, 딥러닝, 안드로이드 개발 in 남룡북매
    출저 부제목: IT에 관심이 많은 동신대 한의대생의 개발일지
    총 글 갯수: 50
    ==============
    카테고리: pythonic practice
    제목: np.random.shuffle 과 np.random.permutation 정리
    내용: <p>1. shuffle은 inplace=True로 섞어준다.</p>
    <p>2. permutation은 array를 반환한다.</p>
    <p>3. permutation에 int1개만 넣으면, 그만큼 np.arange()를 만들어서 0부터 n-1개까지 shuflle후 array를 반환해준다.</p>
    링크: https://nittaku.tistory.com/514
    날짜: 2021-07-26 13:38:29
    ```

### summary(거진 html 태그섞인 것)을 bs4로 text덩어리들만 골라내기 + title도
- 참고: https://github.com/wybiral/firehose/blob/master/parsers/rss/__init__.py

1. 현재 `summary`만 있지만, 어떤 경우 `content`의 value에 내용이 포함되는 경우도 있다. content는 `type`이 `text/html`인 경우 `value`를 꺼내면 된다.
   - 둘 다 추출한 뒤, 가장 짧은 html_body를 1개 꺼낸다.

   ```python
    def _get_shortest_html_body(entry):
        """
        1. 어떤 곳에선 summary 대신 content에 내용이 들어가는 경우도 있으니 2개를 각각 추출해 list로 만든다.
        2. len로 정렬후 짧은 것 1개만 가져간다
        """
        html_body_list = []
        # entry['summary']를 추출
        if 'summary' in entry:
            html_body_list.append(entry.get('summary'))
    
        # entry['content']에서 'type' == 'text/html' 일 때, 'value'를 추출
        if 'content' in entry:
            for content in entry.get('content'):
                if content['type'] != 'text/html':
                    continue
                html_body_list.append(content['value'])
    
        # 2곳에서 다 추출했는데, 한개도 없다면 return None
        if len(html_body_list) == 0:
            return None
    
        # html_body_list의 각 html_body들을 len순으로 정렬한 뒤, 제일 짧은 것을 반환한다
        html_body_list.sort(key=lambda x: len(x))
        return html_body_list[0]
   ```
   ```python
   # print(f'내용: {entry.get("summary")}')
   print(f'내용: {_get_shortest_html_body(entry)}')
   ```


2. bs4를 이용하여 `html.parser`로 파싱한 뒤(내용변화는 없음. 검색만 되는 상태) **`.get_text().strip()`으로 `hrml태그를 다 날린다`**
   ```python
   def _get_text_body(entry):
       html_body = _get_shortest_html_body(entry)
       # <p>1. shuffle은 inplace=True로 섞어준다.</p>
       parsed_body = BeautifulSoup(html_body, 'html.parser')
       # <p>1. shuffle은 inplace=True로 섞어준다.</p>
       
       # 1. shuffle은 inplace=True로 섞어준다.
       return parsed_body.get_text().strip()
   ```
   ```python
    # print(f'내용: {entry.get("summary")}')
    print(f'내용: {_get_text_body(entry)}')
    ```
    ```
    parsed_body>> 
    <p>1. shuffle은 inplace=True로 섞어준다.</p>
    <p>2. permutation은 array를 반환한다.</p>
    <p>3. permutation에 int1개만 넣으면, 그만큼 np.arange()를 만들어서 0부터 n-1개까지 shuflle후 array를 반환해준다.</p>
    
    parsed_body.get_text().strip()>> 
    1. shuffle은 inplace=True로 섞어준다.
    2. permutation은 array를 반환한다.
    3. permutation에 int1개만 넣으면, 그만큼 np.arange()를 만들어서 0부터 n-1개까지 shuflle후 array를 반환해준다.
    ```
    

3. title에도 html태그가 속할 수 있기 때문에 처리한다
    ```python
    def _get_text_title(html_title):
        return BeautifulSoup(html_title, 'html.parser').get_text().strip()
    ```
    ```python
    # print(f'제목: {entry.get("title")}')
    print(f'제목: {_get_text_title(entry.get("title"))}')
    ```


### 각 블로그마다 서로 다른 thumbnail 추출
- `Tistory`: entry의 각종 소스 + `summary`에서 추출 -> **없으면 `opengraph_py3`를 이용해서 각 post의 url이 아닌 `source 블로그 자체url`에서 `og:image`를 추출한다**
    - **현재 `post의 url`로 og:image를 구하면, `Tistory로고`가 나오고, blog_url로 og:image를 구하면 `블로그의 로고`가 나온다.**
    - 참고(entry추출) : feedhose: https://github.com/wybiral/firehose/blob/master/parsers/rss/__init__.py
    - 참고(og:image추출) : rss_to_db: 
- `Naver`: **xml의 entry나 일반 og:image로는 `추출불가능`하다. 본문의 내용을 파싱 -> bs4`img태그를 추출`해야한다.**
    - 과정
        1. `post_url`로 bs4 파싱한 다음 `iframe#mainFrame`을 찾은 뒤, 'src'를 가져와 main_frame_url을 알아낸다.
        2. `main_frame_url`을 bs4로 파싱한 다음, `div#post_1`을 찾고, `data-post-editor-version`을 가져오면, 사용가능한 에디터로 작성된 post이다.
        3. 파싱된 `main_frame_url`에서 `div.se-component`를 select로 여러개의 html components를 찾은 뒤, 순회한다
        4. enumerate로 순회하여 0번째 component인 header component는 건너뛰고, str()으로 바꿔서, `se-component se-image`로 이미지가 들어가있는지 확인한다.
        5. `se-component se-image`를 포함한 component에서 select로 `img태그`들을 찾는다.
        6. img tag에서  `data-lazy-src`속성에 img_url값이 들어가있다. 없으면 건너띄고, 있는 것은 다 구한다.
        7. 기본적으로 첫번째 img_url을 반환한다. 
    - 참고: naverblogbacker : https://github.com/Jeongseup/naver-blog-backer/blob/main/src/naverblogbacker/componentParser.py#L251

#### parser_logger도 따로 준비한다.
```python
# app/utils/loggers.py
parse_logger = Logger("parse").getLogger
```
```python
# app/utils/__init__.py
from .loggers import logger, task_logger, schedule_logger, parse_logger
```
- **from app.utils**으로 시작하려면, app의 init.py가 올라가야하는데 rq땜에 윈도우 에러가 난다
    - create_app으로 구현한다
    - 이 때, create_app 내부에서는 from import *이 안되기 때문에 하나하나 다 import한다
```python
def create_app():
    from .models import Task, Message, Notification
```
```python
# manage.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
```
#### 바로 url을 feedparser하지말고, headers에 User-Agent를 넣은 requests로 요청하기
- 여러번 사용되므로 메서드로 추출하고 예외처리를 한다.
- 예외가 발생할 땐 False로 반환해서, 밖에서 검사한다
```python
#...
from app.utils.loggers import parse_logger

class BaseParser(object):
    def __init__(self, target_id):
        #...
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
        }
    #....
    def requests_url(self, url, params=None):
        try:
            response = requests.get(url, headers=self.headers if not headers else headers, params=params)
            # if response.status_code != 200:
            #     raise requests.HTTPError
            response.raise_for_status()  # Raises :class:`HTTPError`, if one occurred.
            return response.text
        except requests.HTTPError:
            parse_logger.error(f'requests 요청 실패(target_id: {self.target_id}, url: {url})')
            return False

    def parse(self):
        result_text = self.requests_url(self._url)
        if not result_text:
            return False
```


#### tistory thumbnail 가져오기
1. `티스토리`의 경우, summary 등에 없을 경우, blog_url에서 og:image를 추출하기 위해 
    - `self._source_url`에 상태값으로 미리 넣어둔다.
    ```python
    feed = feedparser.parse(result_text)
    # ...
    source = feed['feed']
            
    print(f"출저 타입: {source['generator']}")
    self._source_url = source['link']
    print(f"출저 url: {self._source_url}")
    ```
   
2. `1단계`로서, rss entry로 `_get_thumbnail`메서드로 뽑아낸다.
    ```python
    def _get_thumbnail(entry):
        # 1. 'media_thumbnail'에서 찾아서, 첫번째 것[0]의 url을 챙긴다.
        if 'media_thumbnail' in entry and len(entry['media_thumbnail']) > 0:
            # print('media_thumbnail 에서 발견')
            return entry['media_thumbnail'][0]['url']
        
        # 2. 'media_content'에서 찾아서, 첫번째 것[0]에서 url이 있을시 챙긴다
        if 'media_content' in entry and len(entry['media_content']) > 0:
            if 'url' in entry['media_content'][0]:
                # print('media_content 에서 발견')
                return entry['media_content'][0]['url']
            
        # 3. 'links'에서 찾아서, 각 link 들 중 'type'에 'image'를 포함하는 것들만 모은 뒤, 존재할 경우 첫번째 것[0]의 'href'를 챙긴다
        if 'links' in entry and len(entry['links']) > 0:
            images = [x for x in entry['links'] if 'image' in x['type']]
            if len(images) > 0:
                # print('links 에서 발견')
                return images[0]['href']
    
        # 4. 지금까지 없었는데, summary(body)가 없다면 아예 없는 것이다.
        #    - summary부터는 bs4로 파싱한 뒤, img태그를 찾는다.
        if 'summary' not in entry:
            return None
    
        # No media attachment or thumbnail? look for <img> in body...
        # 4-1. find_all이 아닌 find로 img태그를 찾아보고 없으면 None이다.
        parsed_body = BeautifulSoup(entry['summary'], 'html.parser')
    
        img_tags = parsed_body.find_all('img')
        if img_tags is None:
            return None
    
        for img_tag in img_tags:
            # 4-2. img태그가 있더라도, 1by1 크기를 가진 것은 없느 것이다.
            if img_tag.get('width', None) == '1':
                continue
            # 4-3. img태그의 'src'가 'yIl2AUoC8zA'를 포함하고 있으면 잘못된 이미지다
            if 'yIl2AUoC8zA' in img_tag['src']:
                continue
            # 4-4. my) 발견한 img['src']가 http로 시작하지 않으면, 잘못된 이미지다.
            # ex> thumbnail_url: data:image/png;base64,iVBORw...
            if not img_tag['src'].startswith('http'):
                continue
    
            return img_tag['src']
        else:
            return None
    ```
   
3. **`self._source_url`로부터 OpenGraph를 이용해서, og:image를 추출하는 `_get_og_image_url`메서드를 생성한다.**
    - **이 때, entry단위가 아니라 source(blog)단위로 1번만 구하면 되므로**
    - **`caching개념`으로서, `self._source_og_image_url`을 저장한 뒤, 없을때만 추출하게 한다.**
    ```python
    class BaseParser(object):
        def __init__(self, target_id):
            self._source_url = None
            self._og_image_url = None
    
        def _get_og_image_url(self):
            if self._og_image_url:
                return self._og_image_url
    
            og = OpenGraph(self._source_url, features='html.parser')
            # print(og, type(og))
            if not og.is_valid():
                return None
    
            self._og_image_url = og.get('image', None)
            return self._og_image_url
    ```
   

#### Naver는 rss entries에서 못찾아오니, bs4로 직접 파싱해야한다
```python
def _get_naver_post_image_url(self, post_url, first_image=True):
    result_text = self.requests_url(post_url)
    if not result_text:
        return None

    parsed_post = BeautifulSoup(result_text, features="html.parser")

    main_frame_element = next(iter(parsed_post.select('iframe#mainFrame')), None)
    if main_frame_element is None:
        parse_logger.debug(f'해당 Naver#{self.target_id}에 main_frame_element을 발견하지 못했습니다.')
        return None

    main_frame_url = "http://blog.naver.com" + main_frame_element.get('src')

    main_frame_html = requests.get(main_frame_url).text
    parsed_main_frame = BeautifulSoup(main_frame_html, features="html.parser")


    post_1_div_element = next(iter(parsed_main_frame.select('div#post_1')), None)
    if post_1_div_element is None:
        parse_logger.debug(f'해당 Naver#{self.target_id}에 div#post_1을 발견하지 못했습니다.')
        return None

    post_editor_ver = post_1_div_element.get('data-post-editor-version')
    if post_editor_ver is None:
        parse_logger.debug(f'해당 Naver#{self.target_id}는 지원하지 않는 버전의 에디터를 사용 중...')
        return None

    components_html = parsed_main_frame.select('div.se-component')
    if not components_html:
        parse_logger.debug(f'해당 Naver#{self.target_id}에 div.se-component를 찾을 수 없습니다.')
        return None

    image_urls = []
    for i, component_html in enumerate(components_html):
        if i == 0:
            # 처음에는 무조건 헤더부분의 다큐먼트 타이틀이 나와 pass한다
            continue

        component_string = str(component_html)
        # 이미지 컴포넌트가 아니면 탈락
        if "se-component se-image" not in component_string:
            continue

        for img_tag in component_html.select('img'):
            img_src = img_tag.get('data-lazy-src', None)
            if img_src is None:
                continue
            image_urls.append(img_src)

    # 하나도 없으면 탈락
    if len(image_urls) == 0:
        parse_logger.debug(f'해당 Naver#{self.target_id}에 se-component se-image를 가진 component 속 img태그에 data-lazy-src를 발견하지 못했습니다.')
        return None

    # 하나라도 있으면, 첫번째 것만 반환
    return image_urls[0] if first_image else image_urls
```

#### thumbnail은 2(rss)+1단계(naver)로 추출한다.
```python
for entry in feed.entries:
    print('==============')
    print(f'카테고리: {_get_category(entry.get("tags"))}')
    # print(f'제목: {entry.get("title")}')
    print(f'제목: {_get_text_title(entry.get("title"))}')
    thumbnail = _get_thumbnail(entry) or self._get_og_image_url() or \
                self._get_naver_post_image_url(entry.get("link"))
```