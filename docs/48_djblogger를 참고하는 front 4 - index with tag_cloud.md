- 참고: https://www.youtube.com/watch?v=6e2OdXcYOoY&list=PLOLrQ9Pn6cawJ9CbY-o_kQC4GOWfhCFHq&index=37

### 데이터 세팅
1. main/index.html에 들어갈 main/components/tag-cloud.html을 생성

2. **이제 main route에서 반환하는 feed list와 별개로 tag들을 얻어야한다.**
    - tag대신 category들을 얻어온다.
    - **SourceCategory를 가져오더라도, SourceConfig <-> Source와 sync가 맞는 관계필터링을 해야한다.**
    - get_feeds 내부에 Source-SourceConfig관계필터링을 작성해놓았으므로, 이용하는 get_list 메서드를 작성해서 사용한다
    - **is_htmx_request는 무한스크롤 페이지네이션 템플릿이므로, main접속시에만 걸어준다.**
    ```python
    class SourceCategory(BaseModel):
        @classmethod
        def get_source_config_active_list(cls):
            return cls.query \
                .outerjoin(cls.sources) \
                .filter(cls.source_config_filter()) \
                .all()
    
    @main_bp.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
    
        if is_htmx_request():
            pagination = URLService().get_feeds(page=page)
            time.sleep(0.2)
            return render_template('main/components/feed-list-elements.html',
                                   feeds=pagination.items,
                                   page=pagination.page,
                                   has_next=pagination.has_next
                                   )
        pagination = URLService().get_feeds(page=page)
    
        categories = SourceCategory.get_source_config_active_list()
   
        return render_template('main/index.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next,
                               categories=categories
                               )
    ```


### tag-cloud.html 작성
- 사실상 category-cloud이므로, 이름을 `main/category-cloud.html`으로 변경해서 작성한다.

1. index.html에서 include한다.
2. category-cloud.html에서 기본틀을 작성한다.
    - 일단 cloud 가장 바깥div에서 아래쪽과의 margin을 4로 작성한다 `.mb-4` 
    - 내부div에서는 bottom에 border를 줄 것이기 때문에, custom class `.border-bottom`으로 작성한다.
        - `.border-bottom`은 이전에 작성했었다.
    - `.mb-4>.border-bottom`
    ```html
    <div class="mb-4">
        <div class="border-bottom">
            
        </div>
    </div>
    ```
3. 가장바깥div > border-bottom div 안쪽에서 `div`를 하나 더 개설하여 categories 데이터를 순회하며 `span`태그안에 name을찍되, 클릭도 되어야하므로 `span>a`안에서 찍는다.
    ```html
    <div class="mb-4">
        <div class="border-bottom">
            <div>
                {% for category in categories %}
                    <span>
                        <a href="">
                            {{category.name}}
                        </a>
                    </span>
                {% endfor %}
            </div>
        </div>
    </div>
    ```
   

4. 이제 태그들 위에 글자를 준다. for 순회전에 **소제목으로서 custom font-size를 나중에 갖더라도 h4태그**로 작성하자.
    - 아래태그들과의 간격을 `pb-2`로 주고, 진하게`fw-bold`준다.
    ```html
    <h4 class="pb-2 fw-bold">다양한 RSS Feed Source를 선택해보세요.</h4>
    {% for category in categories %}
    <span>
        <a href="">
            {{category.name}}
        </a>
    </span>
    {% endfor %}
    ```
   

5. h4글자가 너무큰데, h6로 줄이는게 아니라, custom class `fs-14`로 만든다.
    - 14px은 rem으로 0.875이다 (rem to px 검색)
    ```css
    .fs-14 {
        font-size: 0.875rem;
    }
    ```
    ```html
    <h4 class="pb-2 fw-bold fs-14">다양한 RSS Feed Source를 선택해보세요.</h4>
    ```
   

6. **이제 각 `span으로 tag모양`을 class를 통해 `태그모양`을 만든다.**
    - `border border-dark rounded-pill` + `p-1 px-3`로 태그모양을 잡고 
    - `me-1`로 오른쪽으로 간격을 두고 + `mb-2`로 아래행간 간격을 만든다.
    ```html
    <span class="border border-dark rounded-pill p-1 px-3 me-1 mb-2">
        <a href="">
            {{category.name}}
        </a>
    </span>
    ```
7. **대박) span태그는 inline태그라서 행간을 의미하는 `mb-2`가 안먹힌다.**
    - span태그들이 넘쳐흐를 땐, **inline style로 `display: inline-block;`으로 주자.**
    ```html
    {% for category in categories %}
    <span class="border border-dark rounded-pill p-1 px-3 me-1 mb-2"
          style="display: inline-block"
    >
        <a href="" class="fs-15 fw-600 text-decoration-none text-dark">
            {{category.name}}
        </a>
    </span>
    {% endfor %}
    ```
   
8. 태그span 안쪽에 a태그에 글자크기(`fs-15` custom) + `fw-600`(미리만든 커스텀)을 준다.
    - 또한 글자색 + a태그 밑줄 제거를 준다.
    ```css
    .fs-15 {
        font-size: 0.938rem;
    }
    ```
    ```html
    <a href="" class="fs-15 fw-600 text-decoration-none text-dark">
        {{category.name}}
    </a>
    ```
   

9. 태그들과 border사이의 간격을 주기 위해, border div <-> 태그div 사이의 `태그div부모div`에 `pb-2`로 안쪽 여백으로 처리한다.
    ```html
    <div class="mb-4">
        <div class="border-bottom">
            <div class="pb-2">
                <h4 class="pb-2 fw-bold fs-14">다양한 RSS Feed Source를 선택해보세요.</h4>
                {% for category in categories %}
    ```
10. 