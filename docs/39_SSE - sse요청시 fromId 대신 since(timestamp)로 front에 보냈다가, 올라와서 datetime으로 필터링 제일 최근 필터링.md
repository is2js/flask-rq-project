### dump시 @property로 timestamp로 내려보내고, front에서는 since를 업데이트 
1. front에서 Feed__lastLoadedId -> fromId -> from_id넘어왔다가 -> 넘어온 마지막 feed로 업뎃 변수를 `Feed_since`로 변경한다.
    - 백엔드에선 `from_id` 대신 `since`로 받아주며 -> feed정보에는 `feed.published_timestamp`로 내려보낼 예정이다.
    ```js
        let Feed__since = 0;
    
        function Feed__loadMore(category) {
            let url = `/rss/category/${category}`;
            fetchGet(url, {since: Feed__since}).then(body => {
            
        ///
        function Feed__drawFeeds(feeds) {
            console.log(feeds)
    
            if (feeds.length > 0) {
                Feed__since = feeds[feeds.length - 1].id;
            
        ///
        function Feed__drawFeeds(feeds) {
            console.log(feeds)
    
            if (feeds.length > 0) {
                Feed__since = feeds[feeds.length - 1].publishedTimestamp;
            }
    ```
2. 백엔드에서 받는 queryparam을 from_id -> `since`로 변경해준다. **받을 때 타입은 fields.Int -> `fields.Float`로 변경해준다**
    ```python
    class FeedListView(BaseView):
        @use_kwargs({'since': fields.Float(data_key='since')}, location='query')
        @marshal_with(FeedListResponseSchema)
        def get(self, since):
    
    class CategoryFeedListView(BaseView):
        @use_kwargs({'since': fields.Float(data_key='since')}, location='query')
        @marshal_with(FeedListResponseSchema)
        # path 파라미터는 @use_kwargs사용없이 인자로 바로 받는다.
        def get(self, category_name, since):
    ```
   
3. **이 때, 키워드타입으로 since=since를 넣어주고, 내부에서 없으면 다르게 필터링 하게 한다**
    - 또한 내부에서 정순정렬로 만들지말고, **조회후 각 source마다 받은 feeds를 합친 곳에서 정렬하게 한다**
    ```python
    class FeedListView(BaseView):
        # @use_kwargs(FeedListRequestSchema, location='query')
        @use_kwargs({'since': fields.Float(data_key='since')}, location='query')
        @marshal_with(FeedListResponseSchema)
        def get(self, since):
            try:
                feeds = []
                for service in get_current_services():
                    feeds += service.get_feeds(since=since)
    
                # 통합feeds를 published 정순으로 정렬
                feeds.sort(key=lambda feed: feed.published)
            #...
    class CategoryFeedListView(BaseView):
        @use_kwargs({'since': fields.Float(data_key='since')}, location='query')
        @marshal_with(FeedListResponseSchema)
        def get(self, category_name, since):
            try:
                if category_name == 'youtube':
                    service = YoutubeService()
                elif category_name == 'blog':
                    service = BlogService()
                elif category_name == 'url':
                    service = URLService()
                else:
                    raise ValueError(f'Invalid category name : {category_name}')
                feeds = service.get_feeds(since=since)
                
                # 역순으로 조회한 것을 정순 정렬 for front
                feeds.sort(key=lambda f: f.published_timestamp)
        #...
    ```
   

4. **Feed.published를 timestamp로 바꿔서 필터링하는 것이 아니라 `timestamp로 건너갔다가 오는 since를 datetime`으로 재변환해서 published는 그대로 필터링한다**
    - **Feed.published -> published_timestamp + expression의 `@hybrid_property`를 만들고 필터링해봤지만**
    - 필터링식을 만드러도 제대로 필터링이 안됬다. `return func.extract('epoch', cls.published)`로 timestamp변형하나 db레벨에서 시간을 잃어버리는 것 같다
        - 또한, 변환된 속성으로 필터링하면 index적용안되서 더 오래걸릴 것이다.
    - since(float)를 다시 fromtimestamp로 변환한다
        - 이미 utc적용된 것을 since로 바꿧으니 utc적용안해도 된다. 하면 제대로 필터링 안되더라
    ```python
    def _get_feeds(self, source_category_name, target_infos, display_numbers, since=None):
        # cls별 개별 필터링 by source_category_name, target_info_for_filter
        filter_clause = self._create_feed_filter_clause(source_category_name, target_infos)

        # feeds = Feed.query \
        #     .join(Source.feeds) \
        #     .join(Source.source_category) \
        #     .options(joinedload(Feed.source).joinedload(Source.source_category)) \
        #     .filter(filter_clause) \
        #     .order_by(Feed.published.desc()) \
        #     .limit(display_numbers) \
        #     .all()
        query = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(filter_clause)

        if since:
            since = datetime.fromtimestamp(since)
            feeds = query.filter(Feed.published > since) \
                .all()

        else:
            feeds = query.order_by(Feed.published.desc()) \
                .limit(display_numbers) \
                .all()

        # 개별 카테고리별 front에 정순으로 줘야, 역순으로 끼워넣으니, 정순으로 다시 돌리기 -> 외부에서 통합해서 정렬하도록 뺌
        # feeds.sort(key=lambda f: f.published)
        return feeds
    ```
5. 이제 front에 보낼 timestamp를 schema로 작성해줘야한다.
    - 필터링이 사용하지않을 것이니 @property로 작성한다
    ```python
    class Feed(BaseModel):
        #...
        @property
        def published_timestamp(self):
            return self.published.timestamp() if self.published else None
    ```
   - 개별 Feed Schema에 **`fields.Method`를 통해 property를 추가한다**
       - data_key로 camelCase로 준다
   ```python
    class FeedSchema(Schema):
        published_timestamp = fields.Method("get_published_timestamp", data_key='publishedTimestamp')
    
        def get_published_timestamp(self, obj):
            # obj는 직렬화할 Feed 인스턴스입니다.
            # @property로 정의해놓은 published_timestamp 값을 반환합니다.
            return obj.published_timestamp
    ```
   

### 추가 테스트
1. `/sse_test/<channel>`라우트에 event를 보낼 때, 해당 category의 feed를 추가해서 1개가 추가되는지 확인하자.
