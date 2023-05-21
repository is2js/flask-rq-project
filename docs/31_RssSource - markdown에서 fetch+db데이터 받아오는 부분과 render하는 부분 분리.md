- https://github1s.com/zuobin158/rss_task/blob/master/course.py
- https://github1s.com/szewczykmira/rss-scraper/blob/master/exchangerate/rates/exchange_rates.py
- https://github1s.com/gustavosaez/Rss2Telegram/blob/main/rss2telegram.py


### markdown create에서 데이터 받아 저장하는 부분은 따로 빼기
1. Markdown내에서 `fetch_new_feeds`로 request + db저장을 담당하게 한다
    - 이 때, 새로 저장하는 feed가 있을 경우, True 아니면 False로 반환하게 한다
    ```python
    class Markdown:
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            markdown_text = ''
    
            is_updated = self.fetch_new_feeds()
            #...
    
        def fetch_new_feeds(self):
            new_feeds = []
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
                    # - source dict를 Source객체로 바꿔주기 + url로만 존재여부 판단하기
                    feed['source'] = Source.get_or_create(**feed['source'], get_key='url')
    
                    # 1) url로 필터링 + title이 달라질 경우는 update
                    prev_feed = Feed.query.filter_by(url=feed['url']).first()
                    if prev_feed:
                        if feed['title'] != prev_feed.title:
                            prev_feed.update(**feed)
                        continue
    
                    new_feeds.append(Feed(**feed))
    
            if new_feeds:
                parse_logger.info(f'{self.__class__.__name__}에서 new feed 발견')
                session.add_all(new_feeds)
                session.commit()
                return True
            else:
                parse_logger.info(f'{self.__class__.__name__}에서 새로운 feed가 발견되지 않았습니다')
                return False
    ```
   
### 현재 .env에 맞는 데이터 가져오기
1. 이제 Feed데이터를 가져와야하는데
    - **각 Markdown cls를 통해 `source_category_name`을 얻어낸다. db입력시에도 cls별로 했었따**
    ```python
    def get_source_category_name(self):
        return self.__class__.__name__.replace('Markdown', '')
    ```
    ```python
    def fetch_new_feeds(self):
        new_feeds = []
        for source in self.sources:
            # request 작업
            fetch_feeds = source.fetch_feeds()
            # DB 작업
            for feed in fetch_feeds:
                feed['source']['source_category'] = SourceCategory.get_or_create(
                    name=self.get_source_category_name()
                )
    ```
    - **`DB에는 예전에 지정한 target, url데이터`가 쌓였을지라도 `현재 .env -> SourceConfig`에 해당하는 것을 골라내야한다**
        - 그러려면 `Blog or Youtube의 target_id` 혹은 `url의 name` list가 필요하다
        - **targetsource라면 target_id -> Source.target_url에서 골라낸다**
        - **urlsource라면 name -> Source.name에서 골라낸다**
    ```python
    class Markdown:
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            markdown_text = ''
    
            is_updated = self.fetch_new_feeds()
    
            # new_feeds = self.sort_and_truncate_feeds(feeds, display_numbers=display_numbers)
    
            # 현재 cls기준으로 source_category_name을 얻어낸다.
            source_category_name = self.get_source_category_name()
            # TargetSource라면, target_id list가 / URLSource라면 name list를 가져와서, 필터링에 사용할 것이다.
            target_id_or_name_list = self.get_target_or_name_list(source_category_name)
    ```
    ```python
    def get_target_or_name_list(self, source_category_name):
        # if 존재하는 것만 골라온다.
        if source_category_name == 'Blog':
            target_id_or_name_list = [target_id for target_id, category
                                      in
                                      SourceConfig.tistory_target_id_and_categories + SourceConfig.naver_target_id_and_categories
                                      if target_id]
        elif source_category_name == 'Youtube':
            target_id_or_name_list = [target_id for target_id in SourceConfig.youtube_target_ids if target_id]
        else:
            target_id_or_name_list = [target_name for target_url, target_name in SourceConfig.url_and_names if
                                      target_name]
        return target_id_or_name_list

    ```
2. 이제 `source_category_name`과 `target_id_or_name_list`를 가지고 필터링해야한다
    - **Feed를 대상으로 한다**
    - **`관계필터링`을 위해 Source, SourceCategory를 `.join`한다.**
    - **필터링 clause는 `|` 나 `&`로 묶을 수 있다.**
    - 이 때, 
    ```python
    class Markdown:
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            markdown_text = ''
    
            is_updated = self.fetch_new_feeds()
    
            # new_feeds = self.sort_and_truncate_feeds(feeds, display_numbers=display_numbers)
    
            # 현재 cls기준으로 source_category_name을 얻어낸다.
            source_category_name = self.get_source_category_name()
            # TargetSource라면, target_id list가 / URLSource라면 name list를 가져와서, 필터링에 사용할 것이다.
            target_id_or_name_list = self.get_target_or_name_list(source_category_name)
            # source_category_name와 target_id_or_name_list를 이용해서 필터링된 Feed를 가져온다.
            filter_clause = self.create_feed_filter_clause(source_category_name, target_id_or_name_list)
            #...
    ```
    - 이 때, 여러 list 중에 1개라도 or로 포함되면 해당되는 것이므로 **`list comp` + `*[]`분배를 이용해서 여러 조건절을  `or_()`내부에서 생성한다**
    - 또한, **`|`로 체이닝하여 `url은 id포함여부`, `name은 일치여부`를 체이닝한다**
    - 마지막으로 **source_category_name의 조건절은 `&`로 체이닝한다**
    ```python
    def create_feed_filter_clause(self, source_category_name, target_id_or_name_list):
        # WHERE sourcecategory.name = ? AND (
        #           (source.target_url LIKE '%' || ? || '%') OR
        #           (source.target_url LIKE '%' || ? || '%') OR
        #           source.name = ? OR
        #           source.name = ?)
        # 해당 SourceCategory에 있어야하며
        filter_clause = SourceCategory.name == source_category_name
        
        # target_id가 target_url에 포함되거나 => TargetSource용
        filter_clause = filter_clause & or_(
            *[Source.target_url.contains(target_id_or_name) for target_id_or_name in target_id_or_name_list])
        
        # target_name이 Source의 name과 일치 => URLSource용 
        filter_clause = filter_clause | or_(
            *[Source.name.__eq__(target_id_or_name) for target_id_or_name in target_id_or_name_list])

        return filter_clause
    ```
    - Feed를 가져올건데, 관계필터링을 위해 Source와 SouceCategory를 innerjoin한다
    ```python
    class Markdown:
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            markdown_text = ''
    
            is_updated = self.fetch_new_feeds()
    
            # new_feeds = self.sort_and_truncate_feeds(feeds, display_numbers=display_numbers)
    
            # 현재 cls기준으로 source_category_name을 얻어낸다.
            source_category_name = self.get_source_category_name()
            # TargetSource라면, target_id list가 / URLSource라면 name list를 가져와서, 필터링에 사용할 것이다.
            target_id_or_name_list = self.get_target_or_name_list(source_category_name)
    
            # source_category_name와 target_id_or_name_list를 이용해서 필터링된 Feed를 가져온다.
            # Feed를 가져올건데, 관계필터링을 위해 Source와 SouceCategory를 innerjoin한다
            filter_clause = self.create_feed_filter_clause(source_category_name, target_id_or_name_list)
            feeds = Feed.query \
                .join(Source.feeds) \
                .join(Source.source_category) \
                .filter(filter_clause) \
                .order_by(Feed.published.desc()) \
                .limit(display_numbers) \
                .all()
    
            print([f.title for f in feeds])
    ```
   
3. 이제 feed dict가 아닌 Feed 데이터들을 `set_feed_template`에서 입력되게 한다
    ```python
    def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
        markdown_text = ''
    
        is_updated = self.fetch_new_feeds()
    
        # new_feeds = self.sort_and_truncate_feeds(feeds, display_numbers=display_numbers)
    
        # 현재 cls기준으로 source_category_name을 얻어낸다.
        source_category_name = self.get_source_category_name()
        # TargetSource라면, target_id list가 / URLSource라면 name list를 가져와서, 필터링에 사용할 것이다.
        target_id_or_name_list = self.get_target_or_name_list(source_category_name)
    
        filter_clause = self._create_feed_filter_clause(source_category_name, target_id_or_name_list)
        feeds = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .filter(filter_clause) \
            .order_by(Feed.published.desc()) \
            .limit(display_numbers) \
            .all()
    
        utc_updated_at = pytz.utc.localize(datetime.now())
        kst_updated_at = utc_updated_at.astimezone(pytz.timezone('Asia/Seoul'))
        
        markdown_text += TITLE_TEMPLATE.format(title_level, title, kst_updated_at.strftime("%Y-%m-%d %H:%M:%S"))
        markdown_text += self.set_custom()
        markdown_text += TABLE_START
        markdown_text += self.set_feed_template(feed_template, feeds, prefix=self.is_many_sources_or_targets())
        markdown_text += TABLE_END
    ```
4. 개별 set_feed_template을 처리할 때, feed['url']대신 feed.url으로 model데이터가 입력되게 변경한다
    - youtube는 각 채널명인 `Source의 target_name`을 prefix로 필요하고
    - blog, url은 각 블로그명이 아닌 사용자입력 name인 `Source의 name`을 prefix로 필요로 한다
    - **어떻게 됬든, feed와 연결된 source데이터가 필요하다**
    ```python
    class YoutubeMarkdown(Markdown):
        def set_feed_template(self, feed_template, feeds, prefix=None):
            feed_template_result = ''
    
            for feed in feeds:
                feed_text = feed_template.format(
                    feed.url, #feed['url'],
                    feed.thumbnail_url,
                    feed.url,
                    feed.title,
                    # f'<span style="color:black">{feed["source_category_name"]} | </span>' if prefix else '',
                    f'<span style="color:black">{feed.source.target_name} | </span>' if prefix else '',
                    feed.published_string
                )
                feed_template_result += feed_text
    
            return feed_template_result
    
    class BlogMarkdown(Markdown):
        def set_feed_template(self, feed_template, feeds, prefix=None):
            feed_template_result = ''
    
            for feed in feeds:
                feed_text = feed_template.format(
                    feed.url,
                    feed.thumbnail_url,
                    feed.url,
                    feed.title,
                    f'{feed.source.name} | ' if prefix else '',
                    feed.published_string
                )
                feed_template_result += feed_text
    
            return feed_template_result
    ```
   
### Feed조회시 관계필터링  join에 load까지 덧붙이기
1. `.join`이 끝나고 난 뒤, `.options`에 **`원하는 load( 관계칼럼 )`을 체이닝**해서 연결하면 된다.
    - Feed -> `Feed.source` -> `Source.source_category`
    ```python
    class Markdown:
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            filter_clause = self.create_feed_filter_clause(source_category_name, target_id_or_name_list)
            feeds = Feed.query \
                .join(Source.feeds) \
                .join(Source.source_category) \
                .options(joinedload(Feed.source).joinedload(Source.source_category)) \
                .filter(filter_clause) \
                .order_by(Feed.published.desc()) \
                .limit(display_numbers) \
                .all()
    ```
   
2. 메서드로 filter와 같이 뺀다
    ```python
    class Markdown:
        def create(self, title, feed_template, display_numbers, title_level=SourceConfig.TITLE_LEVEL):
            
    
            is_updated = self.fetch_new_feeds()
    
            # new_feeds = self.sort_and_truncate_feeds(feeds, display_numbers=display_numbers)
    
            # 현재 cls기준으로 source_category_name을 얻어낸다.
            source_category_name = self.get_source_category_name()
            # TargetSource라면, target_id list가 / URLSource라면 name list를 가져와서, 필터링에 사용할 것이다.
            target_id_or_name_list = self.get_target_or_name_list(source_category_name)
    
            # source_category_name와 target_id_or_name_list를 이용해서 필터링된 Feed를 가져온다.
            # Feed를 가져올건데, 관계필터링을 위해 Source와 SouceCategory를 innerjoin한다
            feeds = self.get_feeds(source_category_name, target_id_or_name_list, display_numbers)
            utc_updated_at = pytz.utc.localize(datetime.utcnow())
            kst_updated_at = utc_updated_at.astimezone(pytz.timezone('Asia/Seoul'))
            markdown_text = ''
            markdown_text += TITLE_TEMPLATE.format(title_level, title, kst_updated_at.strftime("%Y-%m-%d %H:%M:%S"))
            markdown_text += self.set_custom()
            markdown_text += TABLE_START
            markdown_text += self.set_feed_template(feed_template, feeds, prefix=self.is_many_sources_or_targets())
            markdown_text += TABLE_END
    
            return markdown_text
    ```
   


### db.sqlite를 gitignore에 없애야, action후 git add .를 통해 저장된다.
1. .gitignore에서 db.sqlite제거하기

2. action yml에서 db_logger 뿌려주는 것 추가하기
    ```yaml
    - name: View logs
    run: |
      cat logs/parse.log
      cat logs/db.log
    ```
   
### 추가
1. URL 구독 란에 set_custom으로 구독중인 목록 나타내기
    - Source를 SourceCategory관계필터링으로 가져온 뒤, list를 입력한다
    ```python
    class URLMarkdown(Markdown):
        def set_custom(self):
            custom_result = ''
    
            name_list = Source.query.join(Source.source_category).filter(
                SourceCategory.name == self.get_source_category_name()
            ).all()
    
            name_list = [source.name for source in name_list]
            custom_result += f'''\
    <div align="center">
        📢 <sup><sub><strong>구독대상:</strong> {', '.join(name_list)}</sub></sup>
    </div>
    '''
            return custom_result
    ```
