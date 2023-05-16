1. `python-dotenv` 설치
2. rss_source에 `.env`만들기
    ```python
    # 블로그 설정
    BLOG_DISPLAY_NUMBERS=
    
    TISTORY_TARGET_IDS=nittaku
    TISTORY_CATEGORIES=
    
    NAVER_TARGET_IDS=is2js
    NAVER_CATEGORIES=
    
    # 유튜브 설정
    YOUTUBE_DISPLAY_NUMBERS=5
    
    YOUTUBE_TARGET_IDS=UChZt76JR2Fed1EQ_Ql2W_cw, UC-lgoofOVXSoOdRf5Ui9TWw
    ```
   
3. **콤마로 받은 문자열을 `split(',')`로 무조건 list를 먼저 만들고 각각을 `strip()`한다**
    - **blog에 해당하는 tistory, naver는 category를 list로 취급하고, `itertools.zip_longest`를 통해 짧은 부분(카테고리 없음)을 None으로 채우도록 한다.**
    - youtube는 id list가, tistory/naver는 id, category tuple list가 반환된다.
    ```python
    
    ```
    ```python
    if __name__ == '__main__':
        from pprint import pprint
    
        load_dotenv()
    
    
        blog_display_numbers_or_none = os.getenv('YOUTUBE_DISPLAY_NUMBERS', None)
        BLOG_DISPLAY_NUMBERS = int(blog_display_numbers_or_none) if blog_display_numbers_or_none else 5
    
        tistory_target_ids = [item.strip() if item else None for item in os.getenv('TISTORY_TARGET_IDS').split(',')]
        tistory_categories = [item.strip() if item else None for item in os.getenv('TISTORY_CATEGORIES').split(',')]
        tistory_targets = list(zip_longest(tistory_target_ids, tistory_categories))
        # print(tistory_targets) # [('nittaku', None)]
    
    
        naver_target_ids = [item.strip() if item else None for item in os.getenv('NAVER_TARGET_IDS').split(',')]
        naver_categories = [item.strip() if item else None for item in os.getenv('NAVER_CATEGORIES').split(',')]
        naver_targets = list(zip_longest(naver_target_ids, naver_categories))
        # print(naver_targets) # [('is2js', None)]
    
    
    
        youtube_display_numbers_or_none = os.getenv('YOUTUBE_DISPLAY_NUMBERS', None)
        YOUTUBE_DISPLAY_NUMBERS = int(youtube_display_numbers_or_none) if youtube_display_numbers_or_none else 5
        youtube_target_ids = [item.strip() if item else None for item in os.getenv('YOUTUBE_TARGET_IDS').split(',')]
        # print(youtube_target_ids) # ['UChZt76JR2Fed1EQ_Ql2W_cw', 'UC-lgoofOVXSoOdRf5Ui9TWw']
    ```
   

4. **`target_id가 None`인 경우를 확인하려면, `split으로 인해 항상 list로 들어`오므로 개별 순회하는 메서드인 `TargetSource` 내부 `_generate_urls` 속 `_get_target_url_from_id`를 타기 전에 확인하면 된다.**
    - list map 처리됬던 것을 `검증 + for문으로 변경`한다
    ```python
    class TargetSource(BaseSource):
        TARGET_URL = ''
   
         def __init__(self, target_ids):
             super().__init__()
             self._url_with_categories = self._generate_urls(self.check_category(self.check_type(target_ids)))
   
        def _generate_urls(self, target_id_and_categories):
            """
            :param target_id_and_categories: ('nittaku', 'IT게시판')
            :return:
            """
            # return list(map(
            #     lambda id_and_category: (
            #         self._get_target_url_from_id(id_and_category[0]), id_and_category[1]),
            #     target_id_and_categories
            # ))
            target_urls = []
            for target_id, category in target_id_and_categories:
                if not target_id:
                    raise ValueError(f'{self.__class__.__name__}() 생성시 target_id가 없을 수 없습니다: {target_id}')
    
                target_url = self._get_target_url_from_id(target_id)
                target_urls.append((target_url, category))
            return target_urls
    
        def _get_target_url_from_id(self, target_id):
            return self.TARGET_URL.format(target_id)
           ```
5. 결국에는 TargetSouce의 생성자 내부에서 에러가 날 수 있으니, **각 Source cls 생성자에 try:except를 걸어줘야한다**
    - 해당 Source에 실패하면, 다른 Source로 넘어가야하므로 error만 log를 남기고 넘어간다.
    ```python
    try:
        youtube = Youtube(youtube_target_ids)
        youtube_feeds = youtube.fetch_feeds()

        youtube_feeds.sort(key=lambda f: f['published'], reverse=True)
        youtube_feeds = youtube_feeds[:YOUTUBE_DISPLAY_NUMBERS]

        youtube_markdown_text = '''\
        
        #...
   
        with open("./README.md", "w", encoding='utf-8') as readme:
            readme.write(youtube_markdown_text)
    except Exception as e:
        parse_logger.error(f'fetch 실패: {str(e)}')
    ```
6. **그렇다면 `각 Source별로 markdown text를 성공시만 반환`하고, 파일쓰기는 merge로 해야한다.**
   - markdown text는 각 fetch_feeds를 정렬 + truncate한 뒤, 생성해야한다.

### Youtube내부에서 self.fetch_feeds결과를 이용하는 self.create_markdown 메서로 옮기기
1. 환경변수들을 cls내부에서 쓸 수 있도록, `config.py`로 만들어서 사용할 수 있게 하기
    ```python
    
    from dotenv import load_dotenv
    
    load_dotenv()
    
    
    class SourceConfig:
        ## BLOG
        blog_display_numbers_or_none = os.getenv('YOUTUBE_DISPLAY_NUMBERS', None)
        BLOG_DISPLAY_NUMBERS = int(blog_display_numbers_or_none) if blog_display_numbers_or_none else 5
    
        # TISOTRY
        tistory_target_ids = [item.strip() if item else None for item in os.getenv('TISTORY_TARGET_IDS').split(',')]
        tistory_categories = [item.strip() if item else None for item in os.getenv('TISTORY_CATEGORIES').split(',')]
        tistory_target_id_and_categories = list(zip_longest(tistory_target_ids, tistory_categories))
        # print(tistory_targets) # [('nittaku', None)]
    
        # NAVER
        naver_target_ids = [item.strip() if item else None for item in os.getenv('NAVER_TARGET_IDS').split(',')]
        naver_categories = [item.strip() if item else None for item in os.getenv('NAVER_CATEGORIES').split(',')]
        naver_target_id_and_categories = list(zip_longest(naver_target_ids, naver_categories))
        # print(naver_targets) # [('is2js', None)]
        
        ## YOUTUBE
        youtube_display_numbers_or_none = os.getenv('YOUTUBE_DISPLAY_NUMBERS', None)
        YOUTUBE_DISPLAY_NUMBERS = int(youtube_display_numbers_or_none) if youtube_display_numbers_or_none else 5
        
        youtube_target_ids = [item.strip() if item else None for item in os.getenv('YOUTUBE_TARGET_IDS').split(',')]
        # print(youtube_target_ids) # ['UChZt76JR2Fed1EQ_Ql2W_cw', 'UC-lgoofOVXSoOdRf5Ui9TWw']
    
    ```
   

2. 마크다운 text 생성부분을 일단 Youtube부터 `.create_markdown()` 메서드 내부로 넣는다.
    ```python
    from config import SourceConfig
    
    if __name__ == '__main__':
    
        try:
            youtube = Youtube(SourceConfig.youtube_target_ids)
            markdown = youtube.create_markdown(SourceConfig.YOUTUBE_TITLE,YOUTUBE_FEED_TEMPLATE,SourceConfig.YOUTUBE_DISPLAY_NUMBERS)
            
            with open("./README_youtube.md", "w", encoding='utf-8') as readme:
                readme.write(markdown)
    
        except Exception as e:
            parse_logger.error(f'fetch 실패: {str(e)}')
    ```
   

3. self.fetch_feeds()의 결과물이 존재할 때, sort와 truncate후 마크다운을 생성한다.
    - 환경변수를 이용해서 `self.sort_and_truncate_feeds`를 정의한다
    ```python
    def sort_and_truncate_feeds(self, feeds):
        feeds.sort(key=lambda f: f['published'], reverse=True)
        return feeds[:SourceConfig.YOUTUBE_DISPLAY_NUMBERS]
    ```
4. **youtube의 경우 `UC로 시작하는 채널이 1개만 들어왔을 때, target_id를 이용한 구독하기버튼`을 만들어야하므로 `self._target_id_with_categories`변수를 `self._url_with_categories`전에 받아놓도록 한다.**
    ```python
    class TargetSource(BaseSource):
        TARGET_URL = ''
    
        def __init__(self, target_id_with_categories):
            super().__init__()
            self._target_id_with_categories = self.check_category(self.check_type(target_id_with_categories))
            self._url_with_categories = self._generate_urls(self._target_id_with_categories)
    ```
   
5. create_markdown내부를 작성한다.
    ```python
        def create_markdown(self):
            markdown_text = ''
    
            feeds = self.fetch_feeds()
            if not feeds:
                return markdown_text
    
            feeds = self.sort_and_truncate_feeds(feeds)
    
            title = '''\
    ### 🎞 최근 유튜브    
    <!-- YOUTUBE:START -->
    '''
            markdown_text += title
    
            if len(self.target_id_with_categories) == 1 and self.target_id_with_categories[0][0].startswith('UC'):
                # 채널명(UC~)을 1개만 입력한 경우 구독하기 버튼
                custom_button = '''
    <div align="center">
        <a href="https://www.youtube.com/channel/{}?sub_confirmation=1"><img src="https://img.shields.io/badge/-구독하기-red?style=flat&logo=youtube&logoColor=white" height=35px/></a>
    </div>
    '''.format(self.target_id_with_categories[0][0])
                markdown_text += custom_button
    
            table_start = '''\
    <div align="center">
        <table>
    '''
            markdown_text += table_start
    
            feed_template = '''\
            <tr>
                <td align="center" width="140px" style="background:black;" style="padding:0;">
                    <a href="{}">
                        <img width="140px" src="{}" style="margin:0;">
                    </a>
                </td>
                <td>
                    <a href="{}" style="color:red;text-decoration: none;">
                        <h4>{}{}</h4>
                    </a>
                    <small style="color:grey">{}</small>
                </td>
            </tr>
    '''
    
            for feed in feeds:
                feed_text = feed_template.format(
                    feed['url'],
                    feed['thumbnail_url'],
                    feed['url'],
                    f'<span style="color:black">{feed["source_name"]}) </span>' if len(
                        self.target_id_with_categories) > 1 else '',
                    feed['title'],
                    feed['published_string']
                )
                markdown_text += feed_text
            markdown_text += '''\
        </table>
    </div>
    <!-- YOUTUBE: END -->
    
    '''
    
            return markdown_text
    ```
   

### 각 template에서 추가로 달라지는 부분 환경변수로 빼기
1. title의 level및 title내용이 달라질 수 있으므로 환경변수로 뺀다
   - 기존
       ```python
               title = '''\
       ### 🎞 최근 유튜브    
       <!-- YOUTUBE:START -->
       '''
               markdown_text += title
       ```

   - 변화
       ```python
               title = '''\
       {} {}    
       <!-- YOUTUBE:START -->
       '''.format(SourceConfig.TITLE_LEVEL, SourceConfig.YOUTUBE_TITLE)
               markdown_text += title
       ```
       ```python
       class SourceConfig:
           ## TITLE LEVEL
           TITLE_LEVEL = os.getenv('TITLE_LEVEL', None) or "####"
        
           #... 
        
           ## YOUTUBE
           YOUTUBE_TITLE = os.getenv('YOUTUBE_TITLE', None) or "🎞 최근 유튜브"
       ```
       ```python
       # .env
       TITLE_LEVEL="####"
    
       # 유튜브 설정
       YOUTUBE_TITLE=🎞 최근 유튜브
       YOUTUBE_DISPLAY_NUMBERS=5
       ```
     


2. 이제 각 text부분의 template들을 `대문자 상수`로 변경한 뒤, `templates.py`에 추출해두자
    ```python
    TITLE_TEMPLATE = '''\
    {} {}    
    <!-- START -->
    '''
    
    YOUTUBE_CUSTOM_TEMPLATE = '''
    <div align="center">
        <a href="https://www.youtube.com/channel/{}?sub_confirmation=1"><img src="https://img.shields.io/badge/-구독하기-red?style=flat&logo=youtube&logoColor=white" height=35px/></a>
    </div>
    '''
    
    TABLE_START = '''\
    <div align="center">
        <table>
    '''
    
    TABLE_END = '''\
        </table>
    </div>
    <!-- END -->
    
    '''
    YOUTUBE_FEED_TEMPLATE = '''\
            <tr>
                <td align="center" width="140px" style="background:black;" style="padding:0;">
                    <a href="{}">
                        <img width="140px" src="{}" style="margin:0;">
                    </a>
                </td>
                <td>
                    <a href="{}" style="color:red;text-decoration: none;">
                        <h4>{}{}</h4>
                    </a>
                    <small style="color:grey">{}</small>
                </td>
            </tr>
    '''
    ```
    ```python
        def create_markdown(self):
            markdown_text = ''
    
            feeds = self.fetch_feeds()
            if not feeds:
                return markdown_text
            feeds = self.sort_and_truncate_feeds(feeds)
    
            title = TITLE_TEMPLATE.format(SourceConfig.TITLE_LEVEL, SourceConfig.YOUTUBE_TITLE)
            markdown_text += title
    
            # 채널명(UC~)을 1개만 입력한 경우 구독하기 버튼
            if len(self.target_id_with_categories) == 1 and self.target_id_with_categories[0][0].startswith('UC'):
                custom_button = YOUTUBE_CUSTOM_TEMPLATE.format(self.target_id_with_categories[0][0])
                markdown_text += custom_button
    
            markdown_text += TABLE_START
    
            for feed in feeds:
                feed_text = YOUTUBE_FEED_TEMPLATE.format(
                    feed['url'],
                    feed['thumbnail_url'],
                    feed['url'],
                    f'<span style="color:black">{feed["source_name"]}) </span>' if len(
                        self.target_id_with_categories) > 1 else '',
                    feed['title'],
                    feed['published_string']
                )
                markdown_text += feed_text
    
            markdown_text += TABLE_END
    
            return markdown_text
    ```
   
3. 이제 source마다 `달라지는 부분을 파라미터`로 빼주고, `통째로 달라지는 부분믄 메서드`로 빼준다.
    - `title`이 각 Source마다 달라지고, `feed_template`도 달라질 예정이다.
    - custom_button 넣는 부분과 **feed_template을 채우는 부분**은 메서드로 뺀다
    ```python
        def create_markdown(self, title, feed_template):
            markdown_text = ''
    
            feeds = self.fetch_feeds()
            if not feeds:
                return markdown_text
            feeds = self.sort_and_truncate_feeds(feeds)
    
            markdown_text += TITLE_TEMPLATE.format(SourceConfig.TITLE_LEVEL, title)
            markdown_text += self.set_custom()
            markdown_text += TABLE_START
            markdown_text += self.set_feed_template(feed_template, feeds)
            markdown_text += TABLE_END
    
            return markdown_text
    
        def set_custom(self):
            custom_result = ''
            # 채널명(UC~)을 1개만 입력한 경우 구독하기 버튼
            if len(self.target_id_with_categories) == 1 and self.target_id_with_categories[0][0].startswith('UC'):
                custom_button = YOUTUBE_CUSTOM_TEMPLATE.format(self.target_id_with_categories[0][0])
                custom_result += custom_button
                
            return custom_result
    
        def set_feed_template(self, feed_template, feeds):
            feed_template_result = ''
            for feed in feeds:
                feed_text = feed_template.format(
                    feed['url'],
                    feed['thumbnail_url'],
                    feed['url'],
                    f'<span style="color:black">{feed["source_name"]}) </span>' if len(
                        self.target_id_with_categories) > 1 else '',
                    feed['title'],
                    feed['published_string']
                )
                feed_template_result += feed_text
    
            return feed_template_result
    ```

    ```python
    if __name__ == '__main__':
    
        try:
            youtube = Youtube(SourceConfig.youtube_target_ids)
            markdown = youtube.create_markdown(title=SourceConfig.YOUTUBE_TITLE,feed_template=YOUTUBE_FEED_TEMPLATE,size=SourceConfig.YOUTUBE_DISPLAY_NUMBERS)
    
            with open("./README_youtube.md", "w", encoding='utf-8') as readme:
                readme.write(markdown)
    
        except Exception as e:
            parse_logger.error(f'fetch 실패: {str(e)}')
    ```
   

4. sort_and_truncate_feeds의 `display_numbers`도 달라지니 변수로 받아주자.
    ```python
    def create_markdown(self, title, feed_template, display_numbers):
        markdown_text = ''
    
        feeds = self.fetch_feeds()
        if not feeds:
            return markdown_text
        feeds = self.sort_and_truncate_feeds(feeds, display_numbers=display_numbers)
        #...
        
    def sort_and_truncate_feeds(feeds, display_numbers):
        feeds.sort(key=lambda f: f['published'], reverse=True)
        return feeds[:display_numbers]
    
    ```
    ```python
    try:
        youtube = Youtube(SourceConfig.youtube_target_ids)
        markdown = youtube.create_markdown(
            title=SourceConfig.YOUTUBE_TITLE,
            feed_template=YOUTUBE_FEED_TEMPLATE,
            display_numbers=SourceConfig.YOUTUBE_DISPLAY_NUMBERS
        )
    ```
   
5. title_level은 각 source마다 안바뀌니 keyword로만 뽑아놓는다.
    ```python
    def create_markdown(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
        markdown_text = ''

        feeds = self.fetch_feeds()
        if not feeds:
            return markdown_text
        feeds = self.sort_and_truncate_feeds(feeds, display_numbers=display_numbers)

        markdown_text += TITLE_TEMPLATE.format(title_level, title)
        markdown_text += self.set_custom()
        markdown_text += TABLE_START
        markdown_text += self.set_feed_template(feed_template, feeds)
        markdown_text += TABLE_END

        return markdown_text
    ```

### youtube내 create_markdown 등의 메서드드들을 basesource로 올리기
1. 다 복사해서 올린 뒤 **달라지는 `set_custom, set_feed_template` 중**
    - set_custom은 빈값반환으로 일치 -> 각 source 개별 구현
    - set_feed_template은 **필수구현 개별 구현을 위한 raise NotImplement로 바꾼다.**
    ```python
    def set_custom(self):
        custom_result = ''

        return custom_result

    def set_feed_template(self, feed_template, feeds):
        raise NotImplementedError
    ```
   
2. youtube 내에 `create_markdown, sort_and_truncate_feeds`는 공통이므로 삭제한다.


### 문제는, 여러source로 1 markdown을 만드는 경우도 있으므로 Source cls에 create_markdown을 배정하면 안된다.
1. BaseSource에 있던 `create_markdown`외 소스들을 `markdown_creator.py`를 만들고 cls `Markdown`를 만들어 종속시킨다.
    - **이 때, source가 여러개일 수 있으므로 `sources`를 생성자에서 받는다.**
    ```python
    class Markdown:
    
        def __init__(self, sources):
            self.sources = sources \
                if isinstance(sources, list) else [sources]
    
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            markdown_text = ''
            #...
    
        @staticmethod
        def sort_and_truncate_feeds(feeds, display_numbers):
            feeds.sort(key=lambda f: f['published'], reverse=True)
            return feeds[:display_numbers]
    
        def set_custom(self):
            return ''
    
        def set_feed_template(self, feed_template, feeds, prefix=None):
            raise NotImplementedError
    ```

2. **set_feed_template시 prefix여부를 인자로 받고, 그것을 판단하게 하는 함수 `is_many_sources_or_targets`도 정의한다**
    - **이 때 1source many target(YOUTUBE)이거나 many source(Tistory+Naver)인 경우 prefix=True가 나오게 한다.**
    ```python
    class Markdown:
        #...
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            markdown_text = ''
            #...
            markdown_text += self.set_feed_template(feed_template, feeds, prefix=self.is_many_sources_or_targets())
            markdown_text += TABLE_END
    
            return markdown_text
        def is_many_sources_or_targets(self):
            # youtube의 경우, 1source고정이니, 여러 target-> prefix가 필요하다
            # 그외 tistory나 naver 둘중에 1개의 source만 취하는 경우 -> target이 여러개인 경우 필요하다?!
            if len(self.sources) == 1:
                return len(self.sources[0].target_id_with_categories) > 1
            # source가 여러개인 경우 -> naver + tistory -> prefix가 필요하다.
            elif len(self.sources) > 1:
                return True
            else:
                return False
    ```
   

3. **YoutubuMarkdown cls를 만들고, `부모생성자에 필요한 source`를 target만 받으면 Youtube로 미리 만들어서 들어가게 한다**
    ```python
    class YoutubeMarkdown(Markdown):
        def __init__(self, target_ids):
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
                    feed['url'],
                    feed['thumbnail_url'],
                    feed['url'],
                    f'<span style="color:black">{feed["source_name"]}) </span>' if prefix else '',
                    feed['title'],
                    feed['published_string']
                )
                feed_template_result += feed_text
    
            return feed_template_result
    ```
    ```python
    try:
        youtube = YoutubeMarkdown(SourceConfig.youtube_target_ids)
        markdown = youtube.create(
            title=SourceConfig.YOUTUBE_TITLE,
            feed_template=YOUTUBE_FEED_TEMPLATE,
            display_numbers=SourceConfig.YOUTUBE_DISPLAY_NUMBERS
        )
        with open("./README_youtube.md", "w", encoding='utf-8') as readme:
            readme.write(markdown)
    ```
   
### Blog(Tistory+Naver 등)를 의한 BlogMarkdown cls 생성
1. blog_title 등 환경변수 -> .env + Config 설정
    ```python
    # .env
    # 블로그 설정
    BLOG_TITLE=🎞 최근 블로그zzz
    
    
    class SourceConfig:
        ## BLOG
        BLOG_TITLE = os.getenv('BLOG_TITLE', None) or "📚 최근 블로그"
    ```
   
2. **각각의 target정보만 받아서, sources를 만들어 입력 하나도 없을 경우 에러**
    ```python
    class BlogMarkdown(Markdown):
        def __init__(self, tistory_targets=None, naver_targets=None):
            sources = []
            if tistory_targets:
                sources.append(Tistory(tistory_targets))
            if naver_targets:
                sources.append(Naver(naver_targets))
    
            if not sources:
                raise ValueError(f'BlogMarkdown에 입력된 target들이 존재하지 않습니다.')
    
            super().__init__(sources)
    
        def set_feed_template(self, feed_template, feeds, prefix=None):
            feed_template_result = ''
    
            for feed in feeds:
                feed_text = feed_template.format(
                    feed['url'],
                    feed['thumbnail_url'],
                    feed['url'],
                    f'<span style="color:black">{feed["source_category_name"]}) </span>' if prefix else '',
                    feed['title'],
                    feed['published_string']
                )
                feed_template_result += feed_text
    
            return feed_template_result
    ```
   
3. blog template 준비
    ```python
    # app/rss_sources/templates.py
    BLOG_FEED_TEMPLATE = '''\
            <tr>
                <td align="center" width="120px" style="padding:0;">
                    <a href="{}">
                        <img width="120px" src="{}" style="margin:0;" alt="empty">
                    </a>
                </td>
                <td>
                    <a href="{}" style="color:rebeccapurple;text-decoration: none;">
                        <h5>{}{}</h5>
                    </a>
                    <small style="color:grey">{}</small>
                </td>
            </tr>
    '''
    ```
   
4. test
    ```python
    if __name__ == '__main__':
    
        try:
            blog_markdown = BlogMarkdown(
                tistory_targets=SourceConfig.tistory_target_id_and_categories,
                naver_targets=SourceConfig.naver_target_id_and_categories
            )
            markdown = blog_markdown.create(
                title=SourceConfig.BLOG_TITLE,
                feed_template=BLOG_FEED_TEMPLATE,
                display_numbers=SourceConfig.BLOG_DISPLAY_NUMBERS
            )
    
            with open("./README_blog.md", "w", encoding='utf-8') as readme:
                readme.write(markdown)
    
        except Exception as e:
            parse_logger.error(f'blog markdown 생성 실패: {str(e)}')
    ```
   

### 일반 RSS URLSource도 추가해서 만들어보기
1. URL의 경우 **category필터링 대신 `해당 Source 모듈name`을 같이받아서 -> `자동으로 Source('url')`처리가 되도록 하자**
   - 반면 Target의 경우 category를 필터링하는데 쓰이게 했다.

2. env 및 config 준비
    - **이 때, RSS URL과 cls name을 받는다.**
    ```python
    # 구독RSS URL 설정
    URL_TITLE=📆 관심 RSS 구독
    URL_DISPLAY_NUMBERS=5
    
    URL_NAME=민족의학신문, 왓챠
    URL_LIST=http://www.mjmedi.com/rss/clickTop.xml, https://medium.com/feed/watcha
    ```
    - **여기서는 zip_longest가 아닌 짝이 맞아야하는 zip으로 묶는다.**
    ```python
    class SourceConfig:
        ## URL
        URL_TITLE = os.getenv('URL_TITLE', None) or "📆 관심 RSS 구독"
        URL_DISPLAY_NUMBERS = int(os.getenv('URL_DISPLAY_NUMBERS', None)) or 5
    
        urls = [item.strip() if item else None for item in os.getenv('URL_LIST').split(',')]
        url_names = [item.strip() if item else None for item in os.getenv('URL_NAME').split(',')]
        url_and_names = list(zip(urls, url_names))
    
    ```
   
3. **호출시 `globals()`를 통해 이미 import된 모듈(`from urls import *`)중 해당 name의 URLSource를 자동호출한다**
    ```python
    try:
        url_markdown = URLMarkdown(
            # 민족의학신문("rss_url")
            [globals()[name](url) for url, name in SourceConfig.url_and_names]
        )
        markdown = url_markdown.create(
            title=SourceConfig.URL_TITLE,
            feed_template=URL_FEED_TEMPLATE,
            display_numbers=SourceConfig.URL_DISPLAY_NUMBERS
        )

        with open("./README_url.md", "w", encoding='utf-8') as readme:
            readme.write(markdown)

    except Exception as e:
        parse_logger.error(f'url markdown 생성 실패: {str(e)}')
    ```
   

4. templates.py에 URL FEED TEMPLATE을 따로 준비한다
    ```python
    URL_FEED_TEMPLATE = '''\
            <tr>
                <td align="center" width="120px" style="padding:0;">
                    <a href="{}" style="color:grey;text-decoration: none;">
                        {}{}
                    </a>
                </td>
                <td>
                    <a href="{}" style="color:black;text-decoration: none;">
                        <h5>{}</h5>
                    </a>
                    <small style="color:grey">{}</small>
                </td>
            </tr>
    '''
    ```
   

5. **생성자의 작업을 내부로 옮겨서 URLMarkdown을 정의해주자.**
    - template에 맞게 feed_template을 채워준다.
    ```python
    class URLMarkdown(Markdown):
    
        def __init__(self, url_and_names):
            sources = [globals()[name](url) for url, name in url_and_names]
            if not sources:
                raise ValueError(f'URLMarkdown에 입력된 url_and_names들이 존재하지 않습니다.')
            super().__init__(sources)
    
        def set_feed_template(self, feed_template, feeds, prefix=None):
            feed_template_result = ''
            for feed in feeds:
                feed_text = feed_template.format(
                    feed['source_category_url'],
                    feed['source_category_name'],
                    f"</br><small>{feed['category']}</small>" if feed['category'] else '',
                    feed['url'],
                    feed['title'],
                    feed['published_string']
                )
                feed_template_result += feed_text
    
            return feed_template_result
    ```
### fetch_feeds 및 공통 변경사항
1. parser의 published 변경은 쉬운2번방법 -> 1번방법으로 다시 변경
    ```python
    def parse(self, text):
        for entry in feed.entries:
            # 날짜: 2019-02-21 02:18:24
            # 1) published_parsed + mktime + fromtimestamp + pytz
            utc_published = time_struct_to_utc_datetime(entry.get("published_parsed"))

            # 2) published + datetutil + pytz
            # utc_published = parser.parse(entry.get('published'))
            #### => 쉬운방법으로 할 경우, timezone이 안들어간 utc_published가 생성될 수 있다.
    ```
   
2. fetch_feeds에서 category필터링은 TargetSource의 subclass들만
    ```python
    def fetch_feeds(self):
        total_feeds = []
        #...
        for url, category in self._url_with_categories:
            #...
            for feed in self.parser.parse(result_text):
               if issubclass(self.__class__, TargetSource) and category and not self._is_category(feed, category):
                    continue
    ```
   
3. Markdown create에서 `prefix`를 결정짓는 메서드는 URLMarkdown은 제외
```python
    def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
        #...
        markdown_text += self.set_feed_template(feed_template, feeds, prefix=self.is_many_sources_or_targets())
        markdown_text += TABLE_END

        return markdown_text

    def is_many_sources_or_targets(self):
        if issubclass(self.__class__, URLMarkdown):
            return False
```

4. TITLE_TEMPLATE에 업데이트 시간 반영
```python
TITLE_TEMPLATE = '''\
{} {} <small>(자동 업데이트:{})</small>    
<!-- START -->
'''
```
```python
class Markdown:
    #...
    def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
        #...
        updated_at = pytz.timezone('Asia/Seoul').localize(datetime.now())
        markdown_text += TITLE_TEMPLATE.format(title_level, title, updated_at.strftime("%Y-%m-%d %H:%M:%S"))

```

### import변경 및 외부메서드 정리
1. source들은 이제 Markdown 내부에서 사용되므로 옮겨준다.
    ```python
    from targets import *
    from urls import *
    
    class Markdown:
    ```
   

2. 외부에서 각 markdown얻는 메서드를 빼주고, default.md에서 append해준다
    ```python
    def get_youtube_markdown():
        if not SourceConfig.youtube_target_ids:
            return ''
    
        try:
            youtube_markdown = YoutubeMarkdown(SourceConfig.youtube_target_ids)
            return youtube_markdown.create(
                title=SourceConfig.YOUTUBE_TITLE,
                feed_template=YOUTUBE_FEED_TEMPLATE,
                display_numbers=SourceConfig.YOUTUBE_DISPLAY_NUMBERS
            )
    
        except Exception as e:
            parse_logger.error(f'youtube markdown 생성 실패: {str(e)}')
            return ''
    
    
    def get_blog_markdown():
        if not SourceConfig.tistory_target_id_and_categories and not SourceConfig.naver_target_id_and_categories:
            return ''
    
        try:
            blog_markdown = BlogMarkdown(
                tistory_targets=SourceConfig.tistory_target_id_and_categories,
                naver_targets=SourceConfig.naver_target_id_and_categories
            )
            return blog_markdown.create(
                title=SourceConfig.BLOG_TITLE,
                feed_template=BLOG_FEED_TEMPLATE,
                display_numbers=SourceConfig.BLOG_DISPLAY_NUMBERS
            )
    
        except Exception as e:
            parse_logger.error(f'blog markdown 생성 실패: {str(e)}')
            return ''
    
    
    def get_url_markdown():
        if not SourceConfig.url_and_names:
            return ''
    
        try:
            url_markdown = URLMarkdown(
                # 민족의학신문("rss_url")
                # [globals()[name](url) for url, name in SourceConfig.url_and_names]
                SourceConfig.url_and_names
            )
            return url_markdown.create(
                title=SourceConfig.URL_TITLE,
                feed_template=URL_FEED_TEMPLATE,
                display_numbers=SourceConfig.URL_DISPLAY_NUMBERS
            )
        except Exception as e:
            parse_logger.error(f'url markdown 생성 실패: {str(e)}')
            return ''
    
    
    if __name__ == '__main__':
    
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
   

### 추가 예외처리 변경
1. `zip_longest`으로 인해 blog_id와 category가 아무것도 입력안해도 [`None`, `None`]의 tuple list로 들어오게 된다.
    ```python
    # config.py
    # TISOTRY
    tistory_target_ids = [item.strip() if item else None for item in os.getenv('TISTORY_TARGET_IDS').split(',')]
    tistory_categories = [item.strip() if item else None for item in os.getenv('TISTORY_CATEGORIES').split(',')]
    tistory_target_id_and_categories = list(zip_longest(tistory_target_ids, tistory_categories))
    # print(tistory_targets) # [('nittaku', None)] # [(None, None)]
    ```
   
2. 이 때, markdown 생성자에서 **if 로 검사하면 len 1로 나와 안걸린다.**
    ```python
    class BlogMarkdown(Markdown):
        def __init__(self, tistory_targets=None, naver_targets=None):
            sources = []
            if tistory_targets:
                sources.append(Tistory(tistory_targets))
            if naver_targets:
                sources.append(Naver(naver_targets))
    
            if not sources:
                raise ValueError(f'BlogMarkdown에 입력된 target들이 존재하지 않습니다.')
    
            super().__init__(sources)
    ```
   

3. **BlogMarkdown에서만 [(None, None)]을 검사하기 위해 `self.check_targets`를 정의하여, target_id가 있는 것만 골라내서 확인한다.**
    ```python
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
    ```