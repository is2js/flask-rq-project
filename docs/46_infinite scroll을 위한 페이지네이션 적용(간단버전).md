- 간단버전: chatgpt에서 검색
- 심화버전: has_next 등 : https://github1s.com/is2js/2022_sqlalchemy/blob/HEAD/src/infra/tutorial3/common/pagination.py#L30

1. 일단 main_bp에서 1개의 service만 받도록 한다
2. 각 service의 get_feeds에서 pagination을 적용하기 위해
    - 이미 내부에선 per_page를 환경변수로 사용하고 있으니
    - 현재 page만 kwargs로 받아, if 들어오면 pagination하게 한다
    ```python
    @main_bp.route('/')
    def index():
        # feeds = []
        # for service in get_current_services():
        #     feeds += service.get_feeds()
        #
        # # 통합feeds를 published 정순으로 정렬
        # feeds.sort(key=lambda feed: feed.published)
    
        feeds = URLService().get_feeds(page=1)
    
        return render_template('main/index.html', feeds=feeds)
    ```
    ```python
    def get_feeds(self, since=None, page=None):
        #...
        feeds = self._get_feeds(source_category_name, target_info_for_filter, display_numbers, since=since, page=page)
        return feeds
    ```
    ```python
    def _get_feeds(self, source_category_name, target_infos, display_numbers, 
                   since=None, page=None):
        filter_clause = self._create_feed_filter_clause(source_category_name, target_infos)

        query = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(filter_clause)

        if since:
            since = datetime.fromtimestamp(since)
            feeds = query.filter(Feed.published > since) \
                .all()
        elif page:
             #...
        else:
            feeds = query.order_by(Feed.published.desc()) \
                .limit(display_numbers) \
                .all()
        return feeds

     ```
      

2. **pagination로직은 아래와 같다.**
    1. `필터링`할 거 다하고, order_by를 `id or date`순으로 한다.
    2. `전체페이지 수`가 필요하면, `query.count(): 전체 갯수`를 구한 뒤 -> ((전체 갯수 - 1)// 페이지당 갯수) + 1
        - 0~10개->1페 / 11~20 -> 2페
        - 나누기 10했을 때 몫이  000001, 111112 이런식으로 계산되므로
        - 일단 1을 빼서, 제일 마지막 숫자(10, 20)도  앞에숫자들(0~9, 11~19)와 같이 몫이 나오도록 000000, 11111에 걸리도록 만들어놓고 +1을 해준다.
    3. 본격적으로 `per_page` + `page(현재페이지)`로 시작숫자를 위해 `offset(시작숫자-1)`을 구해야한다.
        - 1페면 처음부터 10개이므로 page-1로 시작해야하낟
        - 2페면 앞에 10개를 빼야하므로 `(page-1) * per_page`갯수로 계산되어야한다
        - 3페도 앖에 20개를 빼야하니 offset은 3-1에서 10개를 곱하면 된다.
    ```python
    elif page:
        query = query.order_by(Feed.published.desc())

        # total_count = query.count()  # 전체 결과 수
        # total_pages = (total_count - 1) // display_numbers + 1  # 전체 페이지 수

        # 페이지에 해당하는 결과 조회
        offset = (page - 1) * display_numbers  # OFFSET 값 계산 (3페 -> 앞에 20개 배기 -> 3-1 * 10)
        feeds = query.limit(display_numbers).offset(offset).all()
    ```
   

