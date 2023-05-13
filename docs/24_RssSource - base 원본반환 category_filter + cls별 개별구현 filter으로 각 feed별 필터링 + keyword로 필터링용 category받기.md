### base_source에 category_filter 정의 및 fetch_feeds에 적용
1. 당장은 staticmethod같지만, 개별cls에선 self.xxx를 사용할 수도 있어서 staticmethod를 안쓴다. 
    ```python
    class BaseSource:
        NAME = ''  # source 이름
        URL = ''  # source 자체 url (not rss)
    
        def __init__(self):
            self._urls = None
            self.parser = RssParser()
            
        def category_filter(self, feed):
            return feed
        
        def fetch_feeds(self):
    
            total_feeds = []
    
            for url in self._urls:
                result_text = requests_url(url)
                # [FAIL] 요청 실패시 넘어가기
                if not result_text:
                    parse_logger.info(f'{self.__class__.__name__}의 url({url})에 대한 request요청에 실패')
                    continue
    
                # [SUCCESS] 요청 성공시 parse(generate)로 feed dict 1개씩 받아 처리하기
                feeds = []
                for feed in self.parser.parse(result_text):
                    # [추가삽입] 부모인 source정보 삽입 -> DB적용시 source의 id로 대체?!
                    feed['source_name'] = self.NAME
                    feed['source_url'] = self.URL
                    
                    # [카테고리 필터링]
                    feed = self.category_filter(feed)
    
                    feeds.append(feed)
    
                total_feeds.extend(feeds)
    
            return total_feeds
    ```

### url만 들어와도 (url, None) or (url, category)로 tuple list가 들어오도록 변경
- 참고: https://vscode.dev/github/wybiral/firehose/blob/master/parsers/rss/__init__.py
1. `BaseSource`에 맨 처음 list를 `check_type`으로 해주는 것은 동일한데, **추후 list 내부가 tuple(url, category)인지 확인하고 아니면 (url, None) 변경해주는 `check_category`를 구현한다**
    ```python
    class BaseSource:
        # ...
        @staticmethod
        def check_category(urls_or_url_with_categories):
            urls_with_category = []
            for element in urls_or_url_with_categories:
                if not isinstance(element, tuple):
                    # category가 같이 안들어왔으면 None으로 채워준다.
                    element = (element, None) 
                    
                urls_with_category.append(element)
            return urls_with_category
    ```
   
2. 각 하위cls에서 category가 달린 tuple list로 적용되도록 한다.
   - `self._urls` -> `self._url_with_categories`로 변경한다.
   ```python
    class BaseSource:
        NAME = ''  # source 이름
        URL = ''  # source 자체 url (not rss)
    
        def __init__(self):
            self._url_with_categories = None
            self.parser = RssParser()
   ```
   ```python
    class URLSource(BaseSource):
        def __init__(self, urls):
            super().__init__()
            self._url_with_categories = self.check_category(self.check_type(urls))
    
    
    class TargetSource(BaseSource):
        def __init__(self, target_ids):
            super().__init__()
            self._url_with_categories = self._generate_urls(self.check_category(self.check_type(target_ids)))
    
        def _generate_urls(self, target_ids):
            raise NotImplemented
    ```
   

3. `self._genearte_urls()`에 input이 달라졌으므로 **개별 TargetSource의 구현을 변경해준다.**
    - **기존 target_id_list -> 이제는 target_id + category list가 input으로 온다.**
    - **target rss url을 만드는 f-string을 -> `{}`포함한 string상수로 정의 => `상수.format(변수)`형태로 변경했다**
    ```python
    class Tistory(TargetSource):
        NAME = '티스토리'
        URL = 'https://www.tistory.com/'
        TARGET_URL = 'https://{}.tistory.com/rss'
    
        def _generate_urls(self, target_id_and_categories):
            # return list(map(lambda x: (f"https://{x[0]}.tistory.com/rss", x[1]), target_id_and_categories))
            return list(map(
                lambda id_and_category: (self.TARGET_URL.format(id_and_category[0]), id_and_category[1]),
                target_id_and_categories
            ))
    ```
4. **이제 _generate_url는  `TargetSource`에서 `공통`이 되었으며, `각 구현cls마다 TARGET_URL stirng`만 지정해주면 된다.**
    ```python
    class TargetSource(BaseSource):
        TARGET_URL = ''
    
        def __init__(self, target_ids):
            super().__init__()
            self._url_with_categories = self._generate_urls(self.check_category(self.check_type(target_ids)))
    
        # def _generate_urls(self, target_ids):
        #     raise NotImplemented
    
        def _generate_urls(self, target_id_and_categories):
            # return list(map(lambda x: (f"https://{x[0]}.tistory.com/rss", x[1]), target_id_and_categories))
            return list(map(
                lambda id_and_category: (self.TARGET_URL.format(id_and_category[0]), id_and_category[1]),
                target_id_and_categories
            ))
    ```
   
5. TargetSource  구현 cls들은 `각자 구현하던 _generate_urls를 제거`하고 -> **`{}`를 포함한 TARGET_URL을 만들어놓는다.**
    ```python
    class Naver(TargetSource):
        NAME = '네이버'
        URL = 'https://www.naver.com/'
        TARGET_URL = 'https://rss.blog.naver.com/{}.xml'
    
        # def _generate_urls(self, target_id_and_categories):
        #     return list(map(lambda x: (f"https://rss.blog.naver.com/{x[0]}.xml", x[1]), target_id_and_categories))
    
    class Tistory(TargetSource):
        NAME = '티스토리'
        URL = 'https://www.tistory.com/'
        TARGET_URL = 'https://{}.tistory.com/rss'
    ```
   
6. **Youtube의 경우, TARGET_URL이 target_id에 의해 달라지기 때문에 `TARGET_URL= 대신 _generate_urls 중 target_url을 추출하는 부분을 메서드로 만들고 재정의` 해줘야한다.**
    - **TargetSource에서, TARGET_URL상수 + target_id로 url만드는 부분을 메서드 `_get_target_url_from_id`로 추출한다.**
    ```python
    class TargetSource(BaseSource):
        def _generate_urls(self, target_id_and_categories):
            """
            :param target_id_and_categories: ('nittaku', 'IT게시판')
            :return:
            """
            return list(map(
                lambda id_and_category: (
                    self._get_target_url_from_id(id_and_category[0]), id_and_category[1]),
                target_id_and_categories
            ))
    
        def _get_target_url_from_id(self, target_id):
            return self.TARGET_URL.format(target_id)
    ```
    - Youtube cls에선 `_get_target_url_from_id`만 재정의하고 **TARGET_URL 상수는 안만들어도 된다.**
    ```python
    class Youtube(TargetSource):
        NAME = '유튜브'
        URL = 'https://www.youtube.com/'
        # TARGET_URL = 'https://{}.tistory.com/rss'
    
        def _get_target_url_from_id(self, target_id):
            """
            상수로 target_id -> target_url을 만들 수 없으니
            id로부터 _generate_urls내부의 target_id로부터 url을 만들어주는 메서드를 오버라이딩해서 재정의
            """
            BASE_URL = 'https://www.youtube.com/feeds/videos.xml?'
            if target_id.startswith("UC"):
                return BASE_URL + '&' + 'channel_id' + '=' + target_id
            elif target_id.startswith("PL"):
                return BASE_URL + '&' + 'playlist_id' + '=' + target_id
            else:
                raise ValueError(f'UC 또는 PL로 시작해야합니다. Unvalid target_id: {target_id}')
    ```
   
7. fetch_feeds 메서드에서 url -> url, category로 순회하면서, **주어진 category가 존재할 때만, category_fileter메서드를 작동하도록 한다**
    - **카테고리에 안맞으면 None을 return -> 외부에서 None이면 continue로 넘어가기**
    ```python
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
                # [추가삽입] 부모인 source정보 삽입 -> DB적용시 source의 id로 대체?!
                feed['source_name'] = self.NAME
                feed['source_url'] = self.URL

                # [카테고리 필터링] 카테고리가 일치하지 않으면 해당feed dict 넘어가기
                if category and not self._is_category(feed, category):
                    continue

                feeds.append(feed)

            total_feeds.extend(feeds)

        return total_feeds
    ```
    ```python
    @staticmethod
    def _is_category(feed, category):
        if feed['category'] != category:
            return None
        return feed
    ```
   

8. test -> Youtube나 URLSource들은 category를 지정하지 않으므로 자동으로 None으로 들어가게 둔다.
    ```python
    if __name__ == '__main__':
        from pprint import pprint
        # Youtube or URLSource들은 category 미반영
        youtube = Youtube('UChZt76JR2Fed1EQ_Ql2W_cw')
        pprint(youtube.fetch_feeds())
        
        # blog의 경우 category 반영 by tuple
        tistory = Tistory(('nittaku', 'pythonic practice'))
        pprint(tistory.fetch_feeds())
    ```