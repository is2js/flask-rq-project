- 참고: https://www.youtube.com/watch?v=FcFk-fBX7kc&list=PLOLrQ9Pn6cawJ9CbY-o_kQC4GOWfhCFHq&index=36
    - codE: https://github.com/JuanLadeira/djblogger/blob/master/web/core/blog/views.py
- 참고2: https://github1s.com/SamEdwardes/htmx-python-course/blob/main/code/ch7_infinite_scroll/ch7_final_video_collector/templates/feed/partials/video_list.html

### htmx 적용하기
1. htmx.js를 `static/js/htmx.js`에 투입 후 `base/base.html`에 body끝에 걸어주기
    ```html
    <body>
        {% block template %}
        {% endblock template %}
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
                integrity="sha384-geWF76RCwLtnZ8qwWowPQNguL3RmwHVBC9FhGdlKrxdiJJigb/j/68SIy3Te4Bkz"
                crossorigin="anonymous"></script>
        
        <script src="/static/js/htmx.min.js?v=1.5.0"></script>
        </body>
    </html>
    ```
   

#### template에서 infinite scroll적용하기
1. **기존 list데이터를 받아 순회하는 jinja 반복문을 따로 `list 반복문 components`로서 빼야한다.**
    - **반복문내 마지막 요소의 부모에 htmx를 걸어 호출되면 -> `해당 반복문 components` + jinja반복문에 걸릴 `다음 page의 list 데이터`만 추가적으로 백엔드에서 내려받을 예정이기 때문이다**
    -`main/components/feed-list-elements.htm` 생성
    - main/index.html에서 container > row > .col-12.col-lg-8 내부  `{% for feed in feeds %}`부터 반복되는 부분들을 components로서 잘라내기
   ```html
   {% for feed in feeds %}
       <a href="" class="text-decoration-none infScroll">
           <div class="card border-0 pb-5 pb-md-3">
               <div class="row">
                   <div class="col-8">
                       <div class="card-body p-0">
                           <div class="pb-2 text-body infScroll-category">{{feed.source.source_category.name}}</div>
                           <h1 class="mb-1 text-body fw-bold">{{feed.title | truncate(50, true, '...') }}</h1>
                           <h2 class="text-muted fs-6 d-none d-sm-block">{{feed.body | truncate(100, true, '...')  }}</h2>
                           <div class="text-muted infScroll-date">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
                       </div>
                   </div>
                   <div class="col-4">
                       <img src="https://picsum.photos/205/115" class="img-fluid float-end" alt="">
                   </div>
               </div>
           </div>
       </a>
   {% endfor %}
   ```
    - components로 잘라내진 부분을 include로 변경
    ```html
    <!-- app/templates/main/index.html-->
    {% extends "base/base.html" %}
    
    {% block title %} Index Page {% endblock title %}
    
    
    {% block template %}
    
    {% include "base/navbar.html" %}
    {% include "main/components/splash.html" %}
    <div class="container pt-5">
        <div class="row">
            <div class="col-12 col-lg-8">
                {% include "main/components/feed-list-elements.html" %}
            </div>
    
            <div class="d-none d-lg-block col-4">
                tag_cloud
            </div>
    
        </div>
    </div>
    
    {% endblock template %}
    ```

2. backend에서는 pagination을 page=1, page=2로 테스트를 먼저 해본다.
    - **먼저 해당route에서, if request.method == 'POST'처럼 `if is_htmx_request():`인자 판단하는 메서드를 만든다.**
    ```python
    def is_htmx_request():
        return 'HX-Request' in request.headers
    ```
   
3. 그냥 접속하면 page=1의 데이터를, htmx로 넘어오면 page=2의 데이터를 list components만 넘겨주도록 한다.
    ```python
   @main_bp.route('/')
    def index():
        if is_htmx_request():
            feeds = URLService().get_feeds(page=2)
            return render_template('main/components/feed-list-elements.html', feeds=feeds)
   
        feeds = URLService().get_feeds(page=1)
        return render_template('main/index.html', feeds=feeds)
    ```
   
4. **이제 `list component`의 반복문 마지막 요소**일 경우만, `revealed`시 `hx-get`요청을 보내도록 한다.
    - `{%if loop.last%}`를 반복문내 사용하면 마지막 요소에만 적용됨.
    ```html
    {% for feed in feeds %}
        <a href="" class="text-decoration-none" {% if loop.last %} hx-trigger="revealed" hx-get="/"{% endif %}>
    ```
    - 여기까지 마지막 요소 노출시 get -> if is_htmx_request -> list 컴포넌트 + page=2 데이터가 합쳐진 render_template이 내려오는데
    - `hx-swap`의 옵션을 주지 않으면, **내려받은 html을 자신의 자식으로서 append해버린다.**
    - **하지만 list component는 `마지막요소`의 `동급레벨`로서, `마지막요소의 부모의 자식들`로 추가되어야한다.**
      - 그러기 위해선 **`hx-swap="afterend"`로 추가해야한다.**
          - https://htmx.org/docs/#swapping
    ```
    Name	Description
    innerHTML: the default, puts the content inside the target element
    outerHTML: replaces the entire target element with the returned content
    afterbegin: prepends the content before the first child inside the target
    beforebegin: prepends the content before the target in the targets parent element
    beforeend: appends the content after the last child inside the target
    afterend: appends the content after the target in the targets parent element
    delete: deletes the target element regardless of the response
    none: does not append content from response (Out of Band Swaps and Response Headers will still be processed)
    ```
    ```html
    <a href="" class="text-decoration-none"
            {% if loop.last %}
            hx-trigger="revealed"
            hx-get="/
            hx-swap="afterend"
            {% endif %}
    >
    ```
   

5. 이제 route에서 **queryparam으로 `page변수`를 받아 -> render시에 넘겨주고, template에서는 `?page={{ page + 1 }}`로 요청하게 한다**
    ```python
    @main_bp.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
    
        if is_htmx_request():
            # feeds = URLService().get_feeds(page=2)
            # return render_template('main/components/feed-list-elements.html', feeds=feeds)
            feeds = URLService().get_feeds(page=page)
            return render_template('main/components/feed-list-elements.html', feeds=feeds, page=page)
    
        # feeds = URLService().get_feeds(page=1)
        # return render_template('main/index.html', feeds=feeds)
        feeds = URLService().get_feeds(page=page)
        return render_template('main/index.html', feeds=feeds, page=page)
    ```
    ```html
    {% for feed in feeds %}
    <!--       hx-get="/"-->
        <a href="" class="text-decoration-none"
           {% if loop.last %}
           hx-trigger="revealed"
           hx-get="/?page={{page + 1}}"
           hx-swap="afterend"
           {% endif %}
        >
    ```
   


#### 백엔드에서 has_next를 포함해서 내려줘, True일때만 드러나는 indicator에 revealed를 설정하여 svg로 scroll시키기
##### backend Paginate객체를 사용하여 has_next와 같이 page, feeds를 반환
1. backend에서 `app/models/pagination.py`를 생성한다
    - https://github1s.com/is2js/2022_sqlalchemy/blob/HEAD/src/infra/tutorial3/common/pagination.py
    - **기존에는 stmt를 받아 처리하거나. 이미 execute된 전체 list를 처리하도록만 되어있다.**
    - stmt처리 대신, query처리로 변경한다.
    ```python
    from __future__ import annotations
    
    import math
    import typing
    
    from sqlalchemy.orm import Query
    
    
    class Pagination:
        # https://parksrazor.tistory.com/457
        def __init__(self, items, total, page, per_page):
            self.items = items
            self.page = page
            self.total = total
    
            # 이전 페이지를 가지고 있으려면, 현재page - 1 = 직전페이지 계산결과가, 실존 해야하는데, 그게 1보다 크거나 같으면 된다.
            #  0 [ 1 2 page ]
            self.has_prev = page - 1 >= 1
            # 이전 페이지 존재유무에 따라서 이전페이지 넘버를 현재page -1 or None 로 만든다.
            self.prev_num = (self.has_prev and page - 1) or None
    
            # 다음 페이지를 가지고 있으려면, 갯수로 접근해야한다.
            # (1) offset할 직전페이지까지의 갯수: (현재page - 1)*(per_page)
            # (2) 현재페이지의 갯수: len(items) => per_page를 못채워서 더 적을 수도 있다.
            # (3) total갯수보다 현재페이지까지의 갯수가 1개라도 더 적어야, 다음페이지로 넘어간다
            self.has_next = ((page - 1) * per_page + len(items)) < total
            # 다음페이지를 갖고 있다면 + 1만 해주면된다.
            self.next_num = page + 1 if self.has_next else None
    
            # total pages 수는, per_page를 나눠서 math.ceil로 올리면 된다.
            # self.pages = math.ceil(total / per_page) + 1
            self.pages = math.ceil(total / per_page) if total else 0
    
            # https://github.com/pallets-eco/flask-sqlalchemy/blob/main/src/flask_sqlalchemy/pagination.py
    
        def iter_pages(self, *,
                       left_edge: int = 2,  # 1페 포함 보여질 갯수,
                       left_current: int = 2,  # 현재로부터 왼쪽에 보여질 갯수,
                       right_current: int = 4,  # 현재로부터 오른쪽에 보여질 갯수,
                       right_edge: int = 2,  # 마지막페이지 포함 보여질 갯수
                       ) -> typing.Iterator[int | None]:
    
            # 1) 전체 페이지갯수를 바탕으로 end특이점을 구해놓는다.
            pages_end = self.pages + 1
            # 2) end특이점 vs1페부터보여질 갯수+1을 비교해, 1페부터 끝까지의 특이점을 구해놓는다.
            left_end = min(left_edge + 1, pages_end)
            # 3) 1페부터 특이점까지를 1개씩 yield로 방출한다.
            yield from range(1, left_end)
            # 4) 만약 페이지끝 특이점과 1페끝 특이점이 같으면 방출을 마친다.
            if left_end == pages_end:
                return
            # 5) 선택한 page(7) - 왼쪽에 표시할 갯수(2) (보정x 현재로부터 윈도우만큼 떨어진 밖.== 현재 제외 윈도우 시작점) -> 5 [6 7]
            #    과 left끝특이점 중 max()를 mid시작으로 본다.
            #   + 선택한page(7) + 오른쪽표시갯수(4) == 11 == 현재포함윈도우밖 == 현재제외 윈도우의 끝점 vs 전체페이지끝특이점중 min을 mid_end로 보낟
            mid_start = max(left_end, self.page - left_current)
            mid_end = min(pages_end, self.page + right_current)
            # 6) mid 시작과 left끝특이점 비교하여 mid가 더 크면, 중간에 None을 개설한다
            if mid_start - left_end > 0:
                yield None
            # 7) mid의 시작~끝까지를 방출한다.
            yield from range(mid_start, mid_end)
            # 8) mid_end와  (페이지끝특이점 - 우측에서 보여질 갯수)를 비교하여 더 큰 것을 right 시작점으로 본다.
            right_start = max(mid_end, pages_end - right_edge)
            # 9) mid_end(특이점)과 right시작점이 차이가 나면 중간에  None을 개설한다.
            if right_start - mid_end > 0:
                yield None
            # 10) right_start부터, page_end까지 방출한다.
            yield from range(right_start, pages_end)
    
    
    def paginate(query, page=1, per_page=10):
        if page <= 0:
            raise AttributeError('page needs to be >= 1')
        if per_page <= 0:
            raise AttributeError('per_page needs to be >= 1')
    
        # print(type(stmt)) # <class 'sqlalchemy.sql.selectable.Select'>
        # print(isinstance(stmt, Select)) # True
        if not isinstance(query, Query):
            total_pages = len(query)  # list의 갯수
            # 1) offset: 앞에서쩨낄 구간의 갯수 = (page - 1(1부터오면 offset구간0되게) )  *  구간의열갯수 만큼 건너띄기
            # 1-1) 직접하기 위해선 per_page(pair)==구간의 열갯수를 이용해서 전체 구간갯수를 구한다.
            # pages = math.ceil(total / per_page)
            # 그러나, 유효성검사는 생략한다.  [알아서 1번]부터 들어오고, Pagination객체 내부에서 존재할때만 page를 내어주기 때문
            # 1-2) 열갯수 * (원하는페이지 -1)만큼을 offset하여 그 이후로 시작하게 한다.
            offset = per_page * (page - 1)
            items = query[offset:]
            # 2) limit으로서, 현재시작에서 열갯수만큼만 가져온다
            # ->  슬라이싱하면, 꽉채워 없으면, 있는것만큼만 가져와준다.
            items = items[:per_page]
    
            return Pagination(items, total_pages, page, per_page)
    
        total = query.count()  # 전체 결과 수
        # total_pages = (total_count - 1) // per_page + 1  # 전체 페이지 수
    
        # 페이지에 해당하는 결과 조회
        offset = (page - 1) * per_page  # OFFSET 값 계산 (3페 -> 앞에 20개 배기 -> 3-1 * 10)
        items = query.limit(per_page).offset(offset).all()
    
        return Pagination(items, total, page, per_page)
    ```
   
2. service에서 `.get_feeds()`에 page=가 들어올 경우, **feeds(list)가 아닌 `paginate( query, page, per_page=)`를 return해주는 것으로 약속한다.**
    - 그동안에 feeds query를 직접 paginate해줬던 것들을 주석처리하고, 내부에서 작동하게 한다.
    ```python
    def _get_feeds(self, source_category_name, target_infos, display_numbers,
                   since=None, page=None):
        # cls별 개별 필터링 by source_category_name, target_info_for_filter
        filter_clause = self._create_feed_filter_clause(source_category_name, target_infos)
        query = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(filter_clause)
        # sse에서 최신데이터 가져오기용
        if since:
            since = datetime.fromtimestamp(since)
            feeds = query.filter(Feed.published > since) \
                .all()

        # pagination용
        elif page:
            query = query.order_by(Feed.published.desc())

            # total_count = query.count()  # 전체 결과 수
            # total_pages = (total_count - 1) // display_numbers + 1  # 전체 페이지 수

            # 페이지에 해당하는 결과 조회
            # offset = (page - 1) * display_numbers  # OFFSET 값 계산 (3페 -> 앞에 20개 배기 -> 3-1 * 10)
            # feeds = query.limit(display_numbers).offset(offset).all()

            return paginate(query, page=page, per_page=display_numbers)

        else:
            feeds = query.order_by(Feed.published.desc()) \
                .limit(display_numbers) \
                .all()

        # 개별 카테고리별 front에 정순으로 줘야, 역순으로 끼워넣으니, 정순으로 다시 돌리기 -> 외부에서 통합해서 정렬하도록 뺌
        # feeds.sort(key=lambda f: f.published)
        return feeds
    ```
   
3. route에서는 paginate()내부에서 반환되는 Pagination객체로 받은 뒤, `feeds, page`외 `has_next`까지 반환받는다.
    - 이 때, is_htmx_request로 넘어와서 추가로 렌더링하는 경우, indicator가 나타날 수 있게 `time.slepp(0.5)`를 걸어준다. (test)
    ```python
    @main_bp.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
    
        if is_htmx_request():
            pagination = URLService().get_feeds(page=page)
            time.sleep(0.5)
            return render_template('main/components/feed-list-elements.html',
                                   feeds=pagination.items,
                                   page=pagination.page,
                                   has_next=pagination.has_next
                                   )
        pagination = URLService().get_feeds(page=page)
        
        return render_template('main/index.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next
                               )
    ```
   

##### front에서 마지막요소에 revealed -> has_next True시에만 떠있는 indicator로 revealed 요청 이동
1. gif처럼 움직이는 svg indicator를 `static/image/htmx/bars.svg`에 준비한다.
    - https://github1s.com/SamEdwardes/htmx-python-course/blob/main/code/ch6_active_search/ch6_final_video_collector/static/img/bars.svg
   
2.  반복문 list component의 부모태그(a)에 넣어둔 `if loop.last + htmx`코드를 제거하고, **`if has_next`시 나타날 `div > img태그`를 넣는다.**
    - 이 때, **`hx-swap`을 `="outerHTML"`로 지정하여 해당 div태그가 반복문list component에서, `div>img -> 똑같은 백엔드에서 내려주는 반복문listcomponent`로 1:1 replace 되게 한다**
    ```html
    {% for feed in feeds %}
    <a href="" class="text-decoration-none">
        <div class="card border-0 pb-5 pb-md-3">
            <div class="row">
                <div class="col-8">
                    <div class="card-body p-0">
                        <div class="pb-2 text-body infScroll-category">{{feed.source.name}}</div>
                        <h1 class="mb-1 text-body fw-bold infScroll-title">{{feed.title | truncate(50, true, '...') }}</h1>
                        <h2 class="text-muted fs-6 d-none d-sm-block">{{feed.body | truncate(100, true, '...')  }}</h2>
                        <div class="text-muted infScroll-date">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
                    </div>
                </div>
                <div class="col-4">
                    <img src="https://picsum.photos/205/115" class="img-fluid float-end" alt="">
                </div>
            </div>
        </div>
    </a>
    {% endfor %}
    
    
    {% if has_next %}
    <div class="text-center"
         hx-trigger="revealed"
         hx-get="/?page={{page + 1}}"
         hx-swap="outerHTML"
    >
        <img src="/static/image/htmx/bars.svg" width="120px"/>
    </div>
    {% else %}
    <div class="text-center">
        <h5> 더이상 데이터가 없습니다. </h5>
    </div>
    {% endif %}
    ```
    
3. 이제 **네트워크 요청시만 보이도록 하기 위해서 `class="htmx-indicator"`를 부모태그(div)에 달아주면 된다.**
    ```html
    <div class="text-center"
         hx-trigger="revealed"
         hx-get="/?page={{page + 1}}"
         hx-swap="outerHTML"
         class="htmx-indicator"
    >
        <img src="/static/image/htmx/bars.svg" width="120px"
        />
    </div>
    ```
    - **하지만, hx요청 태그인 div말고, `자식태그 중` 해당하는 img태그에만 달아줘도 된다.**
    - **img태그만 네트워크요청시 보이게 되고, 나머지는 처음부터 보이지만, outerHTML로 대체된다.**
    ```html
    <div class="text-center"
         hx-trigger="revealed"
         hx-get="/?page={{page + 1}}"
         hx-swap="outerHTML"
    >
        테스트(html-indicator class가 없으므로 첨부터 보임. 그러나 revealed되어 요청끝나면 대체됨)
        <img src="/static/image/htmx/bars.svg" width="120px"
         class="htmx-indicator"
        />
    </div>
    ```

4. **안정화를 위해, htmx-indicator와 같은 htmx css class인 `class="htmx-settling"`을 추가****하여, 응답 로드 후 20ms동안 다른 요소들과 상호작용안되도록 `안정화`시켜준다**
    - 부모태그의css class=""에 달아준다.
    ```html
    <div class="text-center htmx-settling"
         hx-trigger="revealed"
         hx-get="/?page={{page + 1}}"
         hx-swap="outerHTML"
    >
        <img src="/static/image/htmx/bars.svg" width="120px"
         class="htmx-indicator"
        />
    </div>
    ```
   

4. 이제 route에서 time.sleep()을 삭제한다? -> 삭제하면 아예 안보일정도로 빨라서 0.2초로 걸어준다
    ```python
    @main_bp.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
    
        if is_htmx_request():
            pagination = URLService().get_feeds(page=page)
            time.sleep(0.2)
            return render_template('main/components/feed-list-elements.html',
                                   feeds=pagination.items,
                                   page=pagination.page,
                                   has_next=pagination.
        pagination = URLService().get_feeds(page=page)
    
        return render_template('main/index.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next
                               )
    ```