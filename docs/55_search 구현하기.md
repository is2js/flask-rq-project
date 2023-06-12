- 참고: https://github1s.com/JuanLadeira/djblogger/blob/master/web/core/templates/blog/components/search-bar.html
- flask+htmx: https://www.youtube.com/watch?v=-qU3cfU35OE
    - github: https://github1s.com/SamEdwardes/htmx-python-course/blob/main/code/ch6_active_search/ch6_final_video_collector/views/videos.py

### 각 부분에서의 get search form 수정 및 추가

1. 일단 `navbar.html` 및 **`3-col-template.html`에 새롭게 추가될 search form**을 디자인한다.
    - 먼저 navbar.html 속 form수정
    - **search전용이 아니라, `한 화면 일부분으로 include되는 form`이며 `live search를 위한 화면`으로 넘어가야 하므로 `get으로 요청`하자.**
    - 기존
    ```html
    <form class="d-flex" role="search">
        <input class="form-control me-2" type="search" placeholder="Search" aria-label="Search">
        <button class="btn btn-outline-success" type="submit">Search</button>
    </form>
    ```
    - form 
         - route`/feed/search`  action에  method `get`으로 넘어가, `search.html`화면으로 넘어갈 준비를 한다. 
         - **햄버거에선 `col-12` 시작**, **메뉴가 나타나는 lg부터 3만 차지하도록 `col-lg-3` css class**
    - input
        - name `search_text` value는 따로 안줘서 빈칸으로 유지되게 한다?
        - 버튼은 없애고, `form-control` 클래스외 `rounded-pill`을 가진다.
    ```html
    <div class="collapse navbar-collapse" id="navbarSupportedContent">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">

        </ul>
        <form class="d-flex col-12 col-lg-3" role="search" action="{{url_for('main.feed_search') }}">
            <input class="form-control me-2 rounded-pill" type="search" placeholder="Search" aria-label="Search"
                   name="search_text"
            >
        </form>
    </div>
    ```

2. 3-col-template에서 **`content_right 직전`에 항상 존재할 search form을 넣는다.**
    - 여기서는 항상 `col-12`로 유지한 상태고, 아래쪽과 여백을 `pb-5`로 주자
    ```html
    <div class="container" style="max-width:1500px!important;">
        <div class="row">
            <div class="col-navbar">{% block content_left %}{% endblock content_left %}</div>
            <div class="col-12 col-lg-8 pt-5 px-4 px-md-5">{% block content_mid %}{% endblock content_mid %}</div>
            <div class="d-none d-lg-block col-lg-3 pt-5">
                <form class="d-flex col-12  pb-5" role="search" action="{{url_for('main.feed_search') }}">
                    <input class="form-control rounded-pill" type="search" placeholder="Search" aria-label="Search"
                           name="search_text"
                    >
                </form>
                {% block content_right %}{% endblock content_right %}
            </div>
        </div>
    </div>
    ```
3. get form with args가 넘어갈 route `/feed/search`를 만든다.
    - get form `request.form.get('search_text', '')`으로 받을 수 있다. 
        - cf) post form은 `request.form.to_dict()`로 꺼낸다. 
    ```python
    @main_bp.route('/feed/search')
    def feed_search():
        search_text = request.form.get('search_text', '')
    
        return f'{search_text}'
    ```
   

4. 이제 해당 검색어를 contains를 통해 검색한 feeds를 반환해준다.
    - 대소문자를 구분안하고 검색하기 위해 icontains or ilike로 검색해준다.
    - 각 Service별로가 아닌 통합검색이므로, Feed에서 query처리를 처리해야할 듯 하다.
    - **일단 Feed -> Source.feeds -> Source.source_category로 다 join시켜놓고, `SourceCategory.source_config_filter()`를 사용하여 confi필터링을해놓는다.**
    - 그런 뒤, icontains로 search_text를 필터링한다. **이 때, 차 후 pagination(`내부 .count(), .all()`)을 위해, query로 따로 빼놓고 처리한다**
    ```python
    @main_bp.route('/feed/search')
    def feed_search():
        search_text = request.args.get('search_text', '')
    
        query = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(SourceCategory.source_config_filter()) \
            .where(or_(
                Feed.title.icontains(f'%{search_text}%'),
                Feed.body.icontains(f'%{search_text}%'),
            )) \
            .order_by(Feed.created_at.desc())
    
        feeds = query.all()
    
        return render_template('main/search.html',
                               feeds=feeds)
    ```


### search시 live search를 위한 검색화면 페이지 search.html 생성
1. search.html도 category.html처럼 3-col의 구조가 동일하다. 복사한 뒤, content_mid만 수정한다.
    - 일단 category_name대신 **현재 queryparam검색어를 넣을 건데, `route에서 건네주지말고, query_param을 {{request.args.param}}`으로 바로 jinja에서 사용할 수 있다.**
    - span으로 나머지글자들에 회색을 준다.
    ```html
    {% block content_mid %}
    <div class="mx-auto" style="max-width: 683px;">
    <!--    <h1 class="fs-1 fw-bold pb-5">{{request.args}}</h1>-->
        <!--    ImmutableMultiDict([('search_text', 'fg')])-->
        <h1 class="fs-1 fw-bold pb-5">{{request.args.search_text}}
            <span class="text-muted">에 대한 검색 결과입니다.</span>
        </h1>
    
    </div>
    {% endblock content_mid %}    
    ```

2. 일단 구조가 동일한(mid채우는) `feed-list-elements-category.html`를 복사해서 `feed-list-elements-search.html`로 만들어놓고, include해서 테스트한다.
    - **`내부에 htmx요청주소는 달라진다.`**
    ```html
    {% block content_mid %}
    <div class="mx-auto" style="max-width: 683px;">
        <h1 class="fs-1 fw-bold pb-5">{{request.args.search_text}}
            <span class="text-muted">에 대한 검색 결과입니다.</span>
        </h1>
    
        {% include "main/components/feed-list-elements-search.html" %}
    
    </div>
    {% endblock content_mid %}
    ```
3. htmx 요청 주소를 변경한다.
    - 이 때, **`page=`뿐만 아니라 `search_text=`도 queryparam으로서 추가해야한다.**
    - **근데, htmx요청시 search_text를 다시 내려보내지 않아서, 빈값으로 들어간다**
    - **이를 방지하기 위해, jinja query param을 `search_text = {{ request.args.search_text }}`**
    ```html
    {% if has_next %}
    <div class="text-center htmx-settling"
         hx-trigger="revealed"
         hx-get="{{ url_for('main.feed_search', search_text=request.args.search_text, page=page +1 )}}"
         hx-swap="outerHTML"
    >
        <img src="/static/image/htmx/bars.svg" width="120px"
         class="htmx-indicator"
        />
    </div>
    {% else %}
    <div class="text-center">
        <h5> 더이상 데이터가 없습니다. </h5>
    </div>
    {% endif %}
    ```
4. **search전용 페이지는, 결과 없을 때를 대비하여 멘트를 만들어놓는다.**
    - span태그의 멘트만 feeds여부에 따라 다르게 나오게 한다.
    ```html
    {% block content_mid %}
    <div class="mx-auto" style="max-width: 683px;">
        <h1 class="fs-1 fw-bold pb-5">{{request.args.search_text}}
            {% if feeds %}
            <span class="text-muted">에 대한 검색 결과입니다.</span>
            {% else %}
            <span class="text-muted">에 대한 검색 결과가 없습니다.</span>
            {% endif %}
        </h1>
    
        {% include "main/components/feed-list-elements-search.html" %}
    </div>
    {% endblock content_mid %}
    ```
   

   

### 무한스크롤을 위한 htmx + pagination 추가
1. include된 feeds-list-elements들은 내부에서 `if has_next`가 있으면 img표시 revealed시 htmx요청을 한다.
    - **backend에서 pagination후 has_next를 포함해서 내려보내줘야한다.**
    - 그러려면, 시작page를 1을 기본값으로 보내주고 있어야한다.
    - 추가로 include된 category-cloud.html용 categories도 내려보내준다.
    - return시 `feeds by .items` + `has_next` + `page`까지 추가되서 보낸다.
    ```python
    @main_bp.route('/feed/search')
    def feed_search():
        search_text = request.args.get('search_text', '')
        # pagination 1
        page = request.args.get('page', 1, type=int)
    
        query = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(SourceCategory.source_config_filter()) \
            .where(or_(
                Feed.title.icontains(f'%{search_text}%'),
                Feed.body.icontains(f'%{search_text}%'),
            )) \
            .order_by(Feed.created_at.desc())
    
        # pagination 2
        # feeds = query.all()
        pagination = paginate(query, page=page, per_page=10)
    
        categories = SourceCategory.get_source_config_active_list()
    
        # pagination 3
        # return render_template('main/search.html',
        #                        feeds=feeds)
        return render_template('main/search.html',
                               feeds=pagination.items,
                               has_next=pagination.has_next,
                               page=page,
                               categories=categories
                               )
    ```
   

2. **이제 route에서 htmx요청이 올땐, `component`를 return하도록 추가해줘야한다. 안하면 전체페이지가 넘어온다.**
    ```python
    # pagination 4
    if is_htmx_request():
        return render_template('main/components/feed-list-elements-search.html',
                               feeds=pagination.items,
                               has_next=pagination.has_next,
                               page=page,
                               )
    ```
