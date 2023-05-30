- 현재는 published되면, 전체 데이터를 가져와서 앞쪽에 insert한다
- **하지만, 처음에는 몇개만 가져오고, 그 이후로는 마지막 본 것의 다음의 데이터만 가져와야한다.**


1. front에서 전역변수로 `Feed__lastLoadedId`를 0부터 생성하고, `Feed__loadMore`의 fetchGet요청시 fromId로 같이 보낸다
    ```js
        let Feed__lastLoadedId = 0;
    
        function Feed__loadMore(category) {
            let url = `/rss/category/${category}`;
            fetchGet(url, {fromId: Feed__lastLoadedId}).then(body => {
                Feed__drawCategory(body.category);
                Feed__drawCount(body.count);
                Feed__drawFeeds(body.data.feeds);
            })
        }
    ```
   

2. Feed데이터(body)를 반환하는 view들에서 `location='query'`로 쿼리파라미터 fromId를 -> from_id로 받아온다
    - 단순한 것이므로 inline으로 schema없이 처리한다
    ```python
    class FeedListView(BaseView):
        # @use_kwargs(FeedListRequestSchema, location='query')
        @use_kwargs({'from_id': fields.Int(data_key='fromId')}, location='query')
        @marshal_with(FeedListResponseSchema)
        def get(self, from_id):
        #...
    ```
    - **url에서 path파라미터 category_name을 받고 있지만, query파라미터도 `추가로 from_id`를 메서드 매개변수로 받으면 된다.**
    ```python
    class CategoryFeedListView(BaseView):
        @use_kwargs({'from_id': fields.Int( data_key='fromId')}, location='query')
        #...
        @marshal_with(FeedListResponseSchema)
        def get(self, category_name, from_id):
    ```
    - swagger로 테스트하면 `/rss/category/youtube?fromId=3`로 path + query parameter가 동시에 요청이 온다.


3. backend에서는 from_id가 `안들어올 수 잇는 query 파라미터`로서 if 있다면 처리해야한다.
    - 맨 첨 접속은 `없이 or 0`으로 접속될 듯?
    - **만약 있다면 get_feeds()시 sqlalchemy 쿼리가 다르게 작동해야하므로 인자로 받는다.**
```python
    def get(self, category_name, from_id):
        # ...
        if from_id:
            feeds = service.get_feeds(from_id=from_id)
        else:
            feeds = service.get_feeds()

```
```python
def get_feeds(self, from_id=None):
    #...
    feeds = self._get_feeds(source_category_name, target_info_for_filter, display_numbers, from_id=from_id)
    return feeds
```
```python
def _get_feeds(self, source_category_name, target_infos, display_numbers, from_id=None):
    # cls별 개별 필터링 by source_category_name, target_info_for_filter
    filter_clause = self._create_feed_filter_clause(source_category_name, target_infos)
    query = Feed.query \
        .join(Source.feeds) \
        .join(Source.source_category) \
        .options(joinedload(Feed.source).joinedload(Source.source_category)) \
        .filter(filter_clause)

    if from_id:
        feeds = query.filter(Feed.id > from_id) \
            .all()

    else:
        feeds = query.order_by(Feed.published.desc()) \
            .limit(display_numbers) \
            .all()

    # 개별 카테고리별 front에 정순으로 줘야, 역순으로 끼워넣으니, 정순으로 다시 돌리기
    feeds.sort(key=lambda f: f.published)

    return feeds

```

4. **이제 from_id도 front에서 업데이트해줘야 그 이후로만 불러온다.**
   - Feed__drawFeeds 내부의 `feeds` 들 중 `정순으로 내려온 feed의 가장 마지막 인덱스`의 id로 업데이트하면 될것이다.
    ```js
    function Feed__drawFeeds(feeds) {
        console.log(feeds)
    
        if (feeds.length > 0) {
            Feed__lastLoadedId = feeds[feeds.length - 1].id;
        }
    
        feeds.forEach((feed) => {
    ```
   
5. /rss/categories/youtube에 접속해놓고 sse_test/youtube에서 신호를 줘서 id이후 업데이트 되는지 확인한다.
