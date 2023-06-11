- 참고: https://github1s.com/JuanLadeira/djblogger/blob/master/web/core/templates/blog/components/post-list-elements-tag.html

### backend

1. category_cloud에서 a태그 href에 걸어줄 route를 작성한다.
    - 이 때 category들이 순회하고 있는데, `{{category.name}}` 보다는 `{{category.id}}`를 받는게 낳을 듯 하다.?
       - **url에 name으로 표시(route에서 `category/<category_name>`)되기 위해서, slug가 없으니 name으로 받아야할 듯.** 
    - django에서는 tag.slug를 받았다.
    ```python
    @main_bp.route('/category/<name>')
    def feeds_by_category(name):
        
        #feeds = Feed.get_by_category_name(name)
        
        return f"{name}"
        
    ```
   

2. 이제 category_cloud.html에서 a태그 href=""에 해당 route를 걸어본다.
    ```html
    {% for category in categories %}
    <span class="border border-dark rounded-pill p-1 px-3 me-1 mb-2"
          style="display: inline-block"
    >
        <a href="{{url_for('main.feeds_bu_category', name=category.name) }}" class="fs-15 fw-600 text-decoration-none text-dark">
            {{category.name}}
        </a>
    </span>
    {% endfor %}
    ```
   

3. 이제 route에서 해당 category_name으로 Feed들을 찾을 수 있는 메서드를 구현한다.
    - **category.name은 이미 config에 설정된 category만 나타내고 있기 때문에, config필터링 없이 outerjoin후 필터링만 하면 된다.**
    - feed에 source와 source_category를 붙여서 필터링해서 찾아내는 경우는 **rss의 base_service의 `_get_feeds`와 유사하다**
    - **차라리 페이지네이션도 적용된 `해당category_service`를 재활용하자. -> name.lower() -> 그에 따른 Service객체를 생성해서 feed를 가져온다.**
    - **그렇다면, 페이지네이션을 위해 설계된 `index route를 참고`해야한다.**
    - 임시로 `main/index.html`과 htmx+pagination적용을 위한 `main/components/feed-list-elements.html`을 render한다
    ```python
    @main_bp.route('/category/<name>')
    def feeds_bu_category(name):
        category_name = name.lower()  # 비교를 위하 소문자로
    
        if category_name == 'youtube':
            service = YoutubeService()
        elif category_name == 'blog':
            service = BlogService()
        elif category_name == 'url':
            service = URLService()
        else:
            raise ValueError(f'Invalid category name : {category_name}')
    
        page = request.args.get('page', 1, type=int)
    
        if is_htmx_request():
            pagination = service.get_feeds(page=page)
            time.sleep(0.2)
            return render_template('main/components/feed-list-elements.html',
                                   feeds=pagination.items,
                                   page=pagination.page,
                                   has_next=pagination.has_next
                                   )
    
        pagination = service.get_feeds(page=page)
    
        return render_template('main/index.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next,
                               )
    ```
   

### front 
1. 이제 `main/index.html` 대신 `3-col-template.html`을 상속할, `category.html`을 만들어야한다.
    - 기본틀은 `single.html`을 복사해온다.
    - `content_left`의 로고가 있는 `base/navbar-secondary.html`은 그대로 include하는데,
    - **이후 `content_mid`부분을 삭제해주고**
    - **이후 `content_right`부분에서 single-`연관feed` 대신 index처럼 - `footer.html`을 include해준다.**
    ```html
    {% extends "base/3-col-template.html" %}
    
    {% block content_left %}
    {% include "base/navbar-secondary.html" %}
    {% endblock content_left %}
    
    {% block content_mid %}
    
    {% endblock content_mid %}
    
    {% block content_right %}
    {% include "main/components/category-cloud.html" %}
    {% include "base/footer.html" %}
    {% endblock content_right %}
    ```
2. 이제 route에서 `main/category.html`을 render해주되, **footer.html은 필요없지만, `category-cloud.html`에 필요한 categories 데이터를 추가해서 반환해준다.**
    ```python
    @main_bp.route('/category/<name>')
    def feeds_by_category(name):
        category_name = name.lower()  # 비교를 위하 소문자로
        #...
   
        # content_right - category-cloud + footer
        categories = SourceCategory.get_source_config_active_list()
        categories = categories
    
        return render_template('main/category.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next,
                               categories=categories
                               )
    ```
   

3. content_mid를 feeds로 채워넣는다.
    - 그 전에, 현재 category의 name을 표시하기 위해 route에서 name도 넘겨준다.
    ```python
    @main_bp.route('/category/<name>')
    def feeds_by_category(name):
        category_name = name.lower()  # 비교를 위하 소문자로
        
        #...
   
        return render_template('main/category.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next,
                               categories=categories,
                               category_name=name,
                               )
    ```
   
4. index에 있던 feed-list에 비해 화면이 크다 -> **화면이 크면 `style="max-width:"`**를 통해 늘어날 수 있는 제한을 준다.
    - 그리고 항상 가운데 정렬해준다.
    ```html
     {% block content_mid %}
     <div class="mx-auto" style="max-width: 683px;"></div>
     {% endblock content_mid %}
     ```
    - 먼저 category_name부터 `h1.fw-bold`으로 표기해준다. **h1보다 약간 줄이고 싶다면 `fs-1`을 추가한다.**
    ```html
    {% block content_mid %}
    <div class="mx-auto" style="max-width: 683px;">
        <h1 class="fs-1 fw-bold">{{category_name}}</h1>
    </div>
    {% endblock content_mid %}
    ```
5. 내용부분은 `feed-list-elements.html`과 유사하기 때문에 **`feed-list-elements-cateagory.html`으로 복사해서 `include`해준다**
    - `if has_next`부분에서 `htmx`로 요청하는 route주소를 수정해준다.
        - `hx-get="{{ url_for('main.index', page=page+1)}}"` -> `hx-get="{{ url_for('main.feeds_by_category', name=category_name, page=page+1 )}}"`
    - **이 때, htmx요청시에도 route에서 category_name이 지속적으로 반환되어야한다.**
    ```python
    @main_bp.route('/category/<name>')
    def feeds_by_category(name):
        #...
        if is_htmx_request():
            pagination = service.get_feeds(page=page)
            time.sleep(0.2)
            return render_template('main/components/feed-list-elements-category.html',
                                   feeds=pagination.items,
                                   page=pagination.page,
                                   has_next=pagination.has_next,
                                   category_name=name
                                   )
        #...
    ```
    - 이렇게 `feed-list-elements-category.html`를 정의한다.
    ```html
    {% for feed in feeds %}
    <a href="{{feed.absolute_url}}" class="text-decoration-none">
        <div class="card border-0 mb-5 mb-md-3">
            <div class="row">
                <div class="col-8">
                    <div class="card-body p-0">
                        <div class="pb-2 text-body infScroll-category">{{feed.source.name}}</div>
                        <h1 class="mb-1 text-body fw-bold infScroll-title">{{feed.title | truncate(50, true, '...') }}</h1>
                        <h2 class="text-muted fs-6 d-none d-sm-block">{{feed.body | truncate(100, true, '...') }}</h2>
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
    <div class="text-center htmx-settling"
         hx-trigger="revealed"
         hx-get="{{ url_for('main.feeds_bhycategory', name=category_name, page=page+1 )}}"
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
    - category.html에서 include시킨다
    ```html
    {% block content_mid %}
    <div class="mx-auto" style="max-width: 683px;">
        <h1 class="fs-1 fw-bold">{{category_name}}</h1>
        {% include "main/components/feed-list-elements-category.html" %}
    </div>
    {% endblock content_mid %}
    ```
   

6. 이제 category.html과  feed-list-elements-category.html에 간격을 조절한다.
    - h1태그외 feed들 사이에 `pb-5` 간격을 준다.
    ```html
    {% block content_mid %}
    <div class="mx-auto" style="max-width: 683px;">
        <h1 class="fs-1 fw-bold pb-5">{{category_name}}</h1>
        {% include "main/components/feed-list-elements-category.html" %}
    </div>
    {% endblock content_mid %}
    ```
    - `feed-list-elements-category.html`에서는 
        - 이미지부분을 `col-4`-> `col-3`으로 줄이고
        - 그림 부분에 `pt-4`를 준다.
             - `feed-list-elements.html`에는 `pt-3`으로 추가한다
    ```html
    <div class="col-3 pt-4">
        <img src="https://picsum.photos/205/115" class="img-fluid float-end" alt="">
    </div>
    ```