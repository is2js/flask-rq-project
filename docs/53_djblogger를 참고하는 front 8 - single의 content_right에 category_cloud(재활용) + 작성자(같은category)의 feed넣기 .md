### content_right에 caegory_cloud 삽입

1. index.html에 쓰던 `components`인 category-cloud.html을 single.html의 content_right block에 채운다
    - 데이터가 없어서 아무것도 안나온다(render_partials가 아님.. 고려해봐야함.)
    ```html
    {% block content_right %}
    {% include "main/components/category-cloud.html" %}
    {% endblock content_right %}
    ```
   
2. 이제 3-col에서 mid와 같은 `pt-5`을 줘서 위쪽을 맞춘다.
3. single.html에도 category 데이터를 전해줘야한다
    ```python
    @main_bp.route('/feed/<slug>')
    def feed_single(slug):
        # feed = Feed.query.filter_by(slug=slug).first()
        # return f"{feed.to_dict()}"
        feed = Feed.get_by_slug(slug)
        
        categories = SourceCategory.get_source_config_active_list()
        
        return render_template('main/single.html', 
                               feed=feed,
                               categories=categories
                               )
    ```
   
### content_right 아래쪽에 관련(같은category) 5개만 뽑아서 나열하기

1. right의 아래쪽에는 관련feed들을 가져올 생각이다.
    - feed_single route에서 `feed=`외에 `관련된 feed들`로서 **`같은 작성자 or 같은 카테고리 feeds`** 추가로 내려줘야한다
        - **이 때, 관련 feeds가져오는 것은  현재feed의 category를 이용해서 처리한다.**
    - 같은category의 feeds를 가져오는 것은 service에서 복잡하게 가져오므로, service를 활용해야할 듯 하다.
    ```python
    @main_bp.route('/feed/<slug>')
    def feed_single(slug):
        feed = Feed.get_by_slug(slug)
    
        categories = SourceCategory.get_source_config_active_list()
    
        category_name = feed.source.source_category.name.lower() # 비교를 위하 소문자로
        if category_name == 'youtube':
            service = YoutubeService()
        elif category_name == 'blog':
            service = BlogService()
        elif category_name == 'url':
            service = URLService()
        else:
            raise ValueError(f'Invalid category name : {category_name}')
    
        related_feeds = service.get_feeds()[:5] # 기본 10개 가져오는데 5개만
    
        return render_template('main/single.html',
                               feed=feed,
                               categories=categories,
                               related_feeds=related_feeds,
                               )
    ```
   

2. 관련 feed들을 나열하는 것은 **index.html에서 사용되는 `components/feed-list-elements.html`과 유사하므로 `참고해서 작성`한 뒤, `for문부터 components화`시킨다.**
    - **`components`는 이미 container안에서 `for문부터 작성`됬는데**
    - 여기서는 일단 나타났을 때 전체를 채우기 위해 `col-12`부터 시작한다.
    - 순환하기 전에 현재feed의 category부터 소개한다.
    ```html
    {% block content_right %}
    {% include "main/components/category-cloud.html" %}
    
    <div class="col-12">
        <div>More from {{feed.source.source_category.name}} 카테고리</div>
            {% for feed in related_feeds %}
    
            {% endfor %}
    </div>
    
    {% endblock content_right %}
    ```
   

3. 순환하여 Feed소개하는 것은 `components/feed-list-elements.html`를 참고하여 a태그부터 작성한다.
    - a태그는 애초부터 `a.text-decoration-none`으로 작성 시작하자.
        - `a.text-decoration-none`
    - .card는 애초부터 `.card.border-0`과 같이 쓴 뒤, **카드끼리의 간격을 클릭안되도록 margin으로 `.mb-x`를 같이준다**
        - `div.card.border-0.mb-3`
        - 추가로 시작패딩1, 마진바텀3을 준다.
    - div.card의 내부는 `.row`로 시작하여 `이미지부분col` / `글부분을col`을 나누고, 이미지는 바로 img태그 / 글부분에는 `.card-body`안에 내부 텍스트를 작성한다
        - `.row>.col-9+.col-3`
        - 작은부분이 뒤쪽으로 작게 간 거으로 봐서 col-3이 이미지다.
    ```html
    {% block content_right %}
    {% include "main/components/category-cloud.html" %}
    
    <div class="col-12">
        <div>More from {{feed.source.source_category.name}} 카테고리</div>
        {% for feed in related_feeds %}
        <a href="{{feed.absolute_url}}" class="text-decoration-none">
            <div class="card border-0 mb-3">
                .row>.col-9+.col-3
            </div>
        </a>
        {% endfor %}
    </div>
    
    {% endblock content_right %}
    ```
   

4. 이미지가 우측에 있다면 `img.img-fluid`에서 `.float-end`를 추가하여 **`그림이 오른쪽에서부터 시작하여 확대/축소`**하도록 만든 뒤, 특정사이즈 이미지를 `picsum.photos`에서 가져와 올린다.
    - `img-fluid`는 **max-width:100%로서 `원본 width를 최대 + height 오토`를 통해 `최대워본에서 같이 축소`되는**이미지태그를 반응형으로 만든다.
    ```css
    .img-fluid{max-width:100%;height:auto}
    ```
    - `img.img-fluid.float-end`
    ```html
    <div class="col-3">
        <img src="https://picsum.photos/205/115" alt="" class="img-fluid float-end">
    </div>
    ```
    

5. 글자부분(`col-9`)은 `.cardbody.p-0`으로 시작하고, 내부를 span과 h1,h2,div(p대용) 태그들로 채운다.
    - .card-body의 flex: 1 1 auto를 사용해서 확대/축소/원래크기 시작을 만든다.
    ```css
    .card-body{flex:1 1 auto;padding:1rem 1rem}
    ```
    ```html
    <div class="col-9">
        <div class="card-body p-0">
            <span class="small text-dark">{{feed.source.source_category.name}}</span>
            <h1 class="fs-6 text-dark fw-bold">{{feed.title | truncate(20, true, '...') }}</h1>
        </div>
    </div>
    ```
   
6. 각종 간격을 조절한다.
    - 소제목과 순환되는 카드들 사이에 간격을 준다. pb-3
    ```html
    <div class="col-12">
        <div class="pb-3">More from {{feed.source.source_category.name}} 카테고리</div>
        {% for feed in related_feeds %}
    ```
    
7. 이제 전반적인 간격을 조절해준다.
    - 카드(div.card) 자체에 왼쪽여백1으로 소제목에 비해 `카드 왼쪽 들여쓰기`
    - 글자부분(.col-9)의 `기본 우측 패딩을 pe-2로 덮어쓰기`
    ```html
    <div class="card border-0 mb-3 ps-1">
        <div class="row">
            <div class="col-9 pe-2">
                <div class="card-body p-0">
                    <span class="small text-dark">{{feed.source.source_category.name}}</span>
                    <h1 class="fs-6 text-dark fw-bold">{{feed.title | truncate(20, true, '...') }}</h1>
                </div>
            </div>
            <div class="col-3">
                <img src="https://picsum.photos/205/115" alt="" class="img-fluid float-end">
            </div>
        </div>
    </div>
    ```