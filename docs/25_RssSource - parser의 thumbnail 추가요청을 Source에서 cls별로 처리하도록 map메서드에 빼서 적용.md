### 3단계 thumbnail구하는 parse메서드 코드를, 외부에서 처리하도록 변경하기
1. 현재 parser.parse()에서 매번 thumbnail이 entry에서없으면 재요청하고 있다.
    - **하지만, 그 전에 entry(feed) 정보에 의해 필터링 될 수 있고, source cls마다 다르기 때문에, 외부에서 처리하도록 뺀다**
    ```python
    def parse(self, text):
        #...
        for entry in feed.entries:
            #...
            thumbnail = _get_thumbnail(entry) or self._get_og_image_url() or \
                        self._get_naver_post_image_url(entry.get("link"))
            data['thumbnail_url'] = thumbnail
    ```
   
2. entry로 thumbnail을 뽑는 부분만 그대로 두고,`get_og_image_url`은 Tistory에, `_get_naver_post_image_url`는 Naver에 적용되게 한다.
    ```python
    for entry in feed.entries:
        data['thumbnail_url'] = _get_thumbnail(entry)
    ```
   
3. BaseSource의 fetch_feeds메서드 내부에서 if thumbnail_url이 없으면, cls별로 호출할 수 있도록 self `map`메서드를 정의한다.
    - **cls별 재정의할 예정이므로, 처리를 안하는 feed를 위해 `return feed` 그대로 준다.**
    ```python
    def map(self, feed):
        return feed
    ```
    ```python
    class BaseSource:
        # ...
        def fetch_feeds(self):
    
            total_feeds = []
    
            # for url in self._urls:
            for url, category in self._url_with_categories:
                result_text = requests_url(url)
    
                # [FAIL] 요청 실패시 넘어가기
                if not result_text:
                    parse_logger.info(f'{self.__class__.__name__}의 url({url})에 대한 request요청에 실패')
                    continue
    
                # [SUCCESS] 요청 성공시 parse(generate)로 feed dict 1개씩 받아 처리하기
                feeds = []
                for feed in self.parser.parse(result_text):
                    # [카테고리 필터링] 카테고리가 일치하지 않으면 해당feed dict 넘어가기
                    if category and not self._is_category(feed, category):
                        continue
                        
                    # [추가삽입] 부모인 source정보 삽입 -> DB적용시 source의 id로 대체?!
                    feed['source_category_name'] = self.NAME
                    feed['source_category_url'] = self.URL
                    
                    # [변형/추출]
                    feed = self.map(feed)
    
    
                    feeds.append(feed)
    
                total_feeds.extend(feeds)
    
            return total_feeds
    ```
4. og_image를 구하는 메서드는 다른 곳에서도 쓰일 수 있기 때문에, BaseSource에 넣어둔다.
    - **하지만, Source별 저장할게 아니라, url별 og를 뽑는 것이기 때문에, 캐슁할 변수가 없는 상황이다.**
    ```python
    @staticmethod
    def _get_og_image_url(current_url):
        # if self._og_image_url:
        #     return self._og_image_url

        og = OpenGraph(current_url, features='html.parser')
        if not og.is_valid():
            return None

        # self._og_image_url = og.get('image', None)
        return og.get('image', None)
    ```
   

5. 일단 Tistory의 map함수에서 사용한다고 치면, **반드시 그 전에 `entry의 부모feed 속 'link'`가 들어가 있어야한다.**
    - **source의 URL도 아니고, entry의 link도 아닌 `entries순회전 source의 '개별 blog link'`**
    - parse에서 entry순회전 골라낼 수 있는 정보다. `rss url에 대한 일반 url`에 해당한다.
    - **그냥 tistory이미지가 나오더라도 `feed['link']`를 활용해서 og_image를 가져가기로 한다.**
    ```python
    class Tistory(TargetSource):
        NAME = '티스토리'
        URL = 'https://www.tistory.com/'
        TARGET_URL = 'https://{}.tistory.com/rss'
    
        def map(self, feed):
            if not feed['thumbnail_url']:
                feed['thumbnail_url'] = self._get_og_image_url(feed['url'])
    
            return feed
    ```
   

6. naver의 경우, entry, og_image로는 추출이 안되기 때문에, 바로 Naver cls에 `_get_naver_post_image_url`메서드를 옮기고 `map`에서 호출한다
    ```python
    class Naver(TargetSource):
        NAME = '네이버'
        URL = 'https://www.naver.com/'
        TARGET_URL = 'https://rss.blog.naver.com/{}.xml'
    
        def map(self, feed):
            if not feed['thumbnail_url']:
                feed['thumbnail_url'] = self._get_naver_post_image_url(feed['url'])
    
            return feed
    
        @staticmethod
        def _get_naver_post_image_url(post_url, first_image=True):
            result_text = requests_url(post_url)
            if not result_text:
                return None
    
            parsed_post = BeautifulSoup(result_text, features="html.parser")
    
            main_frame_element = next(iter(parsed_post.select('iframe#mainFrame')), None)
            if main_frame_element is None:
                parse_logger.debug(f'해당 Naver blog에서 main_frame_element을 발견하지 못했습니다.')
                return None
    
            main_frame_url = "http://blog.naver.com" + main_frame_element.get('src')
    
            # main_frame_html = requests.get(main_frame_url).text
            main_frame_html = requests_url(main_frame_url)
            parsed_main_frame = BeautifulSoup(main_frame_html, features="html.parser")
    
            post_1_div_element = next(iter(parsed_main_frame.select('div#post_1')), None)
            if post_1_div_element is None:
                parse_logger.debug(f'해당 Naver blog에서 div#post_1을 발견하지 못했습니다.')
                return None
    
            post_editor_ver = post_1_div_element.get('data-post-editor-version')
            if post_editor_ver is None:
                parse_logger.debug(f'해당 Naver blog는서 지원하지 않는 버전의 에디터를 사용 중...')
                return None
    
            components_html = parsed_main_frame.select('div.se-component')
            if not components_html:
                parse_logger.debug(f'해당 Naver blog에서 div.se-component를 찾을 수 없습니다.')
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
                parse_logger.debug(
                    f'해당 Naver blog에서 se-component se-image를 가진 component 속 img태그에 data-lazy-src를 발견하지 못했습니다.')
                return None
    
            # 하나라도 있으면, 첫번째 것만 반환
            return image_urls[0] if first_image else image_urls
    ```
   
7. naver의 경우, blog글에 image가 없을 경우 이미지가 없다 -> **공식홈피의 svg를 추출해 fill='green'으로 바꿔저서 입력해준다.**
    ```python
    def map(self, feed):
        if not feed['thumbnail_url']:
            # 글에 image가 없는 경우, image를 못뽑는다. -> og_image도 일반적으로 바로 안뽑힘 -> images폴더에서 가져오기
            feed['thumbnail_url'] = self._get_naver_post_image_url(feed['url']) or \
                "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='46' height='21'%3E%3Cpath d='M39.322 3.993c1.486 0 2.584.56 3.339 1.519V4.32H46v11.096C46 19.34 43.004 21 39.962 21v-3.083h.114c1.601 0 2.585-.842 2.585-2.5v-1.075c-.755.958-1.853 1.519-3.34 1.519-3.247 0-5.626-2.71-5.626-5.934s2.379-5.934 5.627-5.934zM3.43.426v4.992c.755-.887 1.875-1.425 3.407-1.425 2.997 0 5.467 2.687 5.467 6.168 0 3.48-2.47 6.167-5.467 6.167-1.532 0-2.652-.537-3.407-1.425V16H0V.425h3.43zm22.59 3.567c3.362 0 6.06 2.687 6.06 6.168 0 3.48-2.698 6.167-6.06 6.167-3.362 0-6.061-2.687-6.061-6.167 0-3.481 2.699-6.168 6.06-6.168zM12.62 0c2.783.277 5.307 1.997 5.307 5.625v10.376h-3.43V5.625c0-1.408-.698-2.235-1.877-2.468zM6.152 7.076c-1.707 0-2.945 1.189-2.945 3.085 0 1.895 1.238 3.084 2.945 3.084 1.708 0 2.945-1.189 2.945-3.084 0-1.896-1.237-3.085-2.945-3.085zm19.868.102c-1.609 0-2.846 1.188-2.846 2.983 0 1.794 1.237 2.983 2.846 2.983s2.846-1.189 2.846-2.983c0-1.795-1.237-2.983-2.846-2.983zm13.873-.183c-1.757 0-2.995 1.188-2.995 2.932s1.238 2.932 2.995 2.932c1.757 0 2.995-1.188 2.995-2.932s-1.238-2.932-2.995-2.932z' fill='green' fill-rule='evenodd'/%3E%3C/svg%3E"
    
        return feed
    ```
   

#### map 예시
```python
    def category_filter(self, x):
        parts = x['url'].split('?', 1)
        url = parts[0]
        _, id = url.rsplit('-', 1)
        x['url'] = url
        x['id'] = id
        return x


    def category_filter(self, x):
        _, x['id'] = x['url'].rsplit('?p=', 1)
        return x

    def category_filter(self, x):
        if x['url'].startswith('https://www.bbc.co.uk/sport/'):
            return None
        return x
    def category_filter(self, x):
        if x['url'].startswith('https://www.theguardian.com/football/'):
            return None
        return x
    def category_filter(self, x):
        if 'id' in x:
            if ' at ' in x['id']:
                x['id'], _ = x['id'].split(' at ', 1)
        return x


    def category_filter(self, x):
        _, id = x['url'].split('.com/', 1)
        if '/' in id:
            id, _ = id.rsplit('/', 1)
        x['id'] = id
        return x

    def category_filter(self, x):
        if x['url'].startswith('https://www.washingtonpost.com/opinions/'):
            return None
        if x['url'].startswith('https://www.washingtonpost.com/sports/'):
            return None
        parts = x['url'].split('?')
        x['url'] = parts[0]
        x['id'] = x['url']
        return x
```
```python
async def _update_text(self, db, queue, text, category):
    for x in self.parser.parse(text):
        if category is not None:
            x['category'] = category
        x['source_category_name'] = self.name
        x['source_category_url'] = self.url
        x = self.map(x)
        if x is None:
            continue
        x['id'] = self.module + ':' + x['id']
        inserted = await db.insert(x)
        if inserted:
            await queue.put(x)
```
