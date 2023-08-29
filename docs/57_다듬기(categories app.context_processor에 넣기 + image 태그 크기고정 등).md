1. index route에서 url service로 가져오는데, search의 query문을 참고하여 가져온다.
    ```python
    @main_bp.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
    
        query = Feed.query \
            .join(Source.feeds) \
            .join(Source.source_category) \
            .options(joinedload(Feed.source).joinedload(Source.source_category)) \
            .filter(SourceCategory.source_config_filter()) \
            .order_by(Feed.created_at.desc())
    
        pagination = paginate(query, page=page, per_page=10)
    
        if is_htmx_request():
            time.sleep(0.2)
            return render_template('main/components/feed-list-elements.html',
                                   feeds=pagination.items,
                                   page=pagination.page,
                                   has_next=pagination.has_next
                                   )
    
        categories = SourceCategory.get_source_config_active_list()
    
        return render_template('main/index.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next,
                               categories=categories
                               )
    ```
   

2. categories는 거의 모든 화면에 다 필요해서, create_app에 `app.context_process()`에 inject_categories를 파서 dict로 전달해서 쓰도록 변경
    ```python
    def create_app():
        #...
   
        # 상시 떠있는 데이터 추가
        app.context_processor(inject_categories)
    
        return app
    
    
    def inject_categories():
        from .models import SourceCategory
        categories = SourceCategory.get_source_config_active_list()
    
        return dict(
            categories=categories,
        )
    ```
   - 각 route에서 `categories = SourceCategory.get_source_config_active_list()`와 render_template시 categories=categoreis를 없애준다.

3. 각 `feed-list-elements-x.html`들에서 img태그를 **예시이미지의 size대로 width/height를 강제**하고 none이면, 예시이미지가 들어가도록 변경한다
    - **`축소조절되는 width를 강제` + `축소조절안되는 height는 max-height로 주기` + `object-fit:cover`로 자연스럽게 채우면서 + `img-fluid`로 width축소 -> height auto**
    ```html
    <div class="col-4 ">
        <img src="{{feed.thumbnail_url or 'https://picsum.photos/205/115' }}" class="img-fluid float-end"
             style="width: 205px;max-height:115px;object-fit: cover"
             alt="{{feed.title}}"
        >
    </div>
    ```
4. `single.html`도 `related_feeds`부분도 수정해준다.
    - width강제 + height는 max-height로 강제 + img-fluid + object-fit:cover
    ```html
    <img src="{{feed.thumbnail_url or 'https://picsum.photos/205/115' }}" class="img-fluid float-end"
         style="width: 205px;max-height:115px;object-fit: cover"
         alt="{{feed.title}}"
    >
    ```
   

5. **이제 img태그를 담당하는 `col-`에서 pt를 직접 주지말고, `row에서 item들을 수직 가운데 정렬`시켜버리자.**
    - 높이를 많이 차지하는 글부분col-8에 의해 이미지부분col-4가 높이에 맞춰서 정렬될 것이다.
    - 각 col-의 `pt-x를 삭제`하자.
    ```html
    <div class="row d-flex align-items-center">
        <div class="col-8">
            <div class="card-body p-0">
                <div class="pb-2 text-body infScroll-category">{{feed.source.name}}</div>
                <h1 class="mb-1 text-body fw-bold infScroll-title">{{feed.title | truncate(50, true, '...') }}</h1>
                <h2 class="text-muted fs-6 d-none d-sm-block">{{feed.body | truncate(100, true, '...') }}</h2>
                <div class="text-muted infScroll-date">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
            </div>
        </div>
        <div class="col-4 ">
    <!-- <img src="https://picsum.photos/205/115" class="img-fluid float-end" alt="">-->
            <img src="{{feed.thumbnail_url or 'https://picsum.photos/205/115' }}" class="img-fluid float-end"
                 style="width: 205px;max-height:115px;object-fit: cover"
                 alt="{{feed.title}}"
            >
        </div>
    </div>
    ```