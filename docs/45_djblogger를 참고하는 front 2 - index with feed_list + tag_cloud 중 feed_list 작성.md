- 참고: https://www.youtube.com/watch?v=M6E6MmkxsuI&list=PLOLrQ9Pn6cawJ9CbY-o_kQC4GOWfhCFHq&index=34

### main/index.html template block에  container>row>col 2개로 feed_list / tag_cloude 틀잡기

1. template block안에서 include된 navbar, splash아래에 `.container>.row>.col*2`을 만들어놓고
    - **sm -> lg 일때 모양을 순서대로 class로 준다.**
    ```html
    {% block template %}
    {% include "base/navbar.html" %}
    {% include "main/components/splash.html" %}

    <div class="container">
        <div class="row">
            <div class="col">a</div>
            <div class="col">b</div>
        </div>
    </div>
    {% endblock template %}
    ```
   
2. **크기옵션을 안준 `sm`일 때는 -> 왼쪽col은 `col-12`를 차지 + 오른쪽col은 display: none;을 줄인 `d-none`를 준다**
    ```html
    <div class="container">
        <div class="row">
            <div class="col-12">a</div>
            <div class="d-none">b</div>
        </div>
    </div>
    ```
   
3. **md가 아닌 lg일 때 옵션을 준다.**
    1. 왼쪽col은 8만 차지하게 준다 > `col-lg-8`
    2. **오른쪽col은** 
        1. **d-none을 d-lg일 땐 일단 나오게 -> `d-lg-block`**
        2. lg일 때 나오면 다음줄로 넘어가니 `col`을 줘서 왼쪽-8에 대한 자동나머지를 차지하도록 ->  `col` or `col-4`를 준다.
            - 왼쪽 col-lg-8에 대해 col-4보다 더 크게 주면, 다음row로 넘어가버린다
            - 내 생각엔 자동으로 나머지를 맞추는 col을 주는게 좋을 것 같다.
            - 강의에서는 col-4로 명시한다
    ```html
    <div class="container">
        <div class="row">
            <div class="col-12 col-lg-8">a</div>
            <div class="d-none d-lg-block col-4">b</div>
        </div>
    </div>
    ```
   

### feed list col에서 backend에서 받은 데이터 순회하기
1. 해당 route에서 데이터를 넘겨준다.
    ```python
    @main_bp.route('/')
    def index():
        feeds = []
        for service in get_current_services():
            feeds += service.get_feeds()
    
        # 통합feeds를 published 정순으로 정렬
        feeds.sort(key=lambda feed: feed.published)
    
        return render_template('main/index.html', feeds=feeds)
    
    ```
   

2. 일단 클릭되는 것을 생각하지 않고 **p태그로 title만 뿌려본다.**
    ```html
    <div class="container">
        <div class="row">
            <div class="col-12 col-lg-8">
                {% for feed in feeds %}
                    <p>{{feed.title}}</p>
                {% endfor %}
            </div>
    
            <div class="d-none d-lg-block col-4">
            </div>
            
        </div>
    </div>
    ```
   
3. 이제 article(feed) 어디라도 클릭이 될 수 있게 p태그 대신 `a태그`로 바꾸고, 안에는 `div태그`를 만들어서 구성할 준비를 한다.
    - **a태그만 있으면 inline이라서 한줄로 붙게 된다. -> `a>div`로 구성되면 내부 div때문에 줄이 넘어간다.**
        - `div`는 기본적으로 `display:block;`을 css로 가진다.
        - **다음요소는 다음줄로 넘어가면서 + a태그가 line 전체에 먹히게 된다.**
        ```css
        div {
            display: block;
        }
        ``` 
    ```html
    <div class="col-12 col-lg-8">
        {% for feed in feeds %}
            <a href="" class="">
                <div>
                    {{feed.title}}
                </div>
            </a>
        {% endfor %}
    </div>
    ```
   
4. a태그 안에 구조를 잡아줄 `div`에  **image와 같이 구성하기 위해 `card`클래스**를 주면 
    - div의 display: block -> `position: relative;` + `display: flex;` + `flex-direction: column;`으로 **자동으로 `flex`가 되며**
    - 회색 border가 생긴다. -> **이 때 `border-0`옵션으로 보더를 제거할 수 있다.**
    ```html
    <div class="col-12 col-lg-8">
        {% for feed in feeds %}
            <a href="" class="">
                <div class="card border-0">
                    {{feed.title}}
                </div>
            </a>
        {% endfor %}
    </div>
    ```
    - **a태그 내부 요소들이 밑줄이 생기지 않게 a태그의 class에 `text-decoration-none` 클래스를 추가한다.**
    ```html
    <a href="" class="text-decoration-none">
    ```
   
5. 반복되는 card들은 a>div.card 가운데, **`가장 바깥의 a태그의 mb-`이 아닌, `내부의 div.card에서 pb-`로 간격을 준다.**
    - flex면서 border-0을 준 card에게는 `pb-`도 기본적으로 준다고 생각하자
    - pb small일 때는 3 -> md부터는 5로 주도록 한다.
    ```html
     <div class="col-12 col-lg-8">
        {% for feed in feeds %}
            <a href="" class="">
                <div class="card border-0 pb-3 pb-md-5">
                    {{feed.title}}
                </div>
            </a>
        {% endfor %}
    </div>
    ```
   

6. 이제 flex + border-0인 `card내부를` 다시 한번 row + `col-8 + col-4 2개`로 나눠 글(div.card-body예정) + image(img태그예정)로 나눈다.
    - `.row>.col-8+.col-4`
    ```html
    <div class="card border-0 pb-3 pb-md-5">
        <div class="row">
            <div class="col-8">
                {{feed.title}}
            </div>
            <div class="col-4">
                image
            </div>
        </div>
    </div>
    ```

7. **`flex` card에 대해 `card-body`를 col-8의 feed list 글작성란에 사용한다.**
    - 아래보는 것과 같이 `flex: 1 1 auto`와 `padding`을 가지고 있는데 **`card-body p-0`을 사용하여 패딩은 없애서 일반 div처럼 사용할 예정이다.**
    - 이 때, **`1 1 auto`**는 
        - **flex-grow:1로서 컨테이너 내부 item이 container 여유공간에 따라 확장가능하게 하여 `부모 컨테이너에 따라 늘려지고`**
        - **flex-shrink:1로서 컨테이너 내부 item이 container를 초과할시 그에 따라 축소하여 `부모 컨테이너보다 넘치면 맞춰서 축소되고`**
        - **flex-basis:auto로서 컨테이너 내부 item이 처음 시작할 때 `item내부 컨텐츠에 따라서 자동 크기 조절되어 시작`되도록 한다**
    ```css
    card-body{flex:1 1 auto;padding:1rem 1rem}
    ```
    ```html
    <div class="card border-0 pb-3 pb-md-5">
        <div class="row">
            <div class="col-8">
                <div class="card-body p-0">
                    <div class="pb-2 text-body">{{feed.source.source_category.name}}</div>
                    {{feed.title}}
                </div>
            </div>
            <div class="col-4">
                image
            </div>
        </div>
    </div>
    ```
8. card-body p-0의 안쪽에 텍스트들을 표시할 건데
    1. 작성자 or cateogry: card-body안에 `작성자 or category`는 1줄을 다 차지하니 span대신 `div태그`로 작성하면 되며, 아래 title에 대비 `pb-` + `text-body`(검은색 글자)로 속성을 준다.
    2. title: `h1`태그 + `mb-1`로 아래와의 간격을 만든다. 
         - **div태그와 같은 `공간개념이 아니므로 padding 대신 margin으로 간격 조절`.**
    3. subtitle or body일부: `h2` 태그 + **아래가 붙어있는 시간이라서 아래와의 간겨없이 글자색만 `text-muted`**
    4. 날짜: 역시 제목이 아니므로 `div`태그 + **마지막 요소라 아래와의 간겨없이 글자색만 `text-muted`**
    ```html
    <a href="" class="text-decoration-none">
        <div class="card border-0 pb-3 pb-md-5">
            <div class="row">
                <div class="col-8">
                    <div class="card-body p-0">
                        <div class="pb-2 text-body">{{feed.source.source_category.name}}</div>
                        <h1 class="mb-1">{{feed.title}}</h1>
                        <h2 class="text-muted">{{feed.body[:30] }}</h2>
                        <div class="text-muted">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
                    </div>
                </div>
                <div class="col-4">
                    image
                </div>
            </div>
        </div>
    </a>
    ```
   
9. 참고로 feed.published(utc로 저장) 된 것을 @prorperty를 이용해서 kst로 바꾸고 -> strftime을 이용해 문자열로 표시했다.
    - pytz kst를 만들고 -> 현재 datetime utc를 pytz utc로 replace한 뒤, pytz kst로 변환
    ```python
    class Feed(BaseModel):
        #...
        @property
        def kst_published(self):
            kst_tz = pytz.timezone('Asia/Seoul')
            utc_dt = self.published.replace(tzinfo=pytz.UTC)
            kst_dt = utc_dt.astimezone(kst_tz)
            return kst_dt
    ```
   

10. 이제 row의 col-4에 `img`태그를 넣는데
    1. **`img-fluid`를 통해서 `해당 이미지의 최대 가로100% 높이auto가 적용`되어 `부모 축소시 같이 줄어들기`가 된다.**
    ```css
    .img-fluid{max-width:100%;height:auto}.
    ```
    - 또한 `float-end`를 통해 **부모 요소내 우측정렬 되도록하여 부모col-4에 대해 `이미지가 좀 작더라도 우측끝에 라인을 맞춰서 시작하게 한다`**
        - img-fluid로 인해 이미지를 100%로 늘렸어도  col-4를 못채울 경우, 우측부터 채우게 한다.
    ```css
    .float-end{float:right!important}
    ```  
    - 이제 img태그가 col-4에 대해, `축소시 같이 축소 & 우측정렬`이 되는 상태이므로 **`https://picsum.photos/`에서 예시 이미지를 찾는다**
        -205/115 크기의 이미지를 넣어보자.
    ```html
    <div class="col-4">
        <img src="https://picsum.photos/205/115" class="img-fluid float-end" alt="">
    </div>
    ```
    

11. feed list container자체가 위족 border와 너무 붙어있어서 `pt-5`로 패딩을 통해 위쪽과 간격을 준다.
    ```html
    <div class="container pt-5">
    ```
    

12. 이제 h1, h2태그로 작성했던 title, subtitle을 **`글자체 적용 등을 위해 h1, h2태그를 유지한체 fs-4, fs-6로 조절`한다.**
    - title에 대해서는 색깔을 `text-body`, 굴기를 `fw-bold`로 주자.
    - title, subtitle에 대해서 jinja 필터로 `| truncate`를 해야한다.
    ```html
    <div class="card-body p-0">
        <div class="pb-2 text-body">{{feed.source.source_category.name}}</div>
        <h1 class="mb-1 fs-4 text-body fw-bold">{{feed.title | truncate(50, true, '...') }}</h1>
        <h2 class="text-muted fs-5">{{feed.body | truncate(100, true, '...')  }}</h2>
        <div class="text-muted">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
    </div>
    ``` 
    

### custom css로 title(h1)용 반응형 fs 만들고 적용 + subtitle(h2)는 sm부터 나타나도록 적용
- fontsize cls인 `fs-`는 반응형 `fs-md-x` 등이 없다. **그래서 실제 구현하려면 custom class를 작성하고 미디어쿼리까지 작성해줘야한다.**
1. `h1`태그에 대해 `fs-4`를 대신하는 반응형을 만들기 위해서는 **모든 h1태그가 지정되면 안되니, `반복되는 것 중 가장 부모인 a태그`에 custom class `infScroll`을 만든 뒤, css에 `infscroll h1`으로 잡아서 처리해줘야한다.**
    ```html
    {% for feed in feeds %}
        <a href="" class="text-decoration-none infScroll">
            <div class="card border-0 pb-5 pb-md-3">
                <div class="row">
                    <div class="col-8">
                        <div class="card-body p-0">
                            <div class="pb-2 text-body">{{feed.source.source_category.name}}</div>
                            <h1 class="mb-1 fs-4 text-body fw-bold">{{feed.title | truncate(50, true, '...') }}</h1>
                            <h2 class="text-muted fs-6">{{feed.body | truncate(100, true, '...')  }}</h2>
                            <div class="text-muted">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
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
   
2. `.infScroll h1` {} 및 미디어쿼리를 작성하기 전 **작아지기 전 글자크기(fs-4)를 실제 값으로 나타내야한다.**
    - cf) css 선택자 콤마: or / 띄워쓰기: and (자식들 중 1개)
    - computed로 확인해보니 22.xxx px이다
    - fs-4를 대신하는 `font-size: 22px;`외 글자간도 큰화면에서는 -0.6px 줄여준다. `letter-spacing: -0.6px;`
    ```css
    .infScroll h1 {
        font-size: 22px;
        letter-spacing: -0.6px;
    }
    ```
    - **미디어 쿼리를 작성할 때는 bootstrap의 breakpoint를 확인하면 된다.**
        - sm은 576이상 / md는 768이상이다.
        - **`max-width: 768px`를 지정하면 `sm을 그리는 것`이다.**
        - 똑같이 `.infScroll h1`에 대해서 적용한다
        - **글자크기를 22px -> 0.9375rem(15px) / 자간은 0으로 적용한다.**
    ```css
    .infScroll h1 {
        font-size: 22px;
        letter-spacing: -0.6px;
    }
    
    @media only screen and (max-width: 768px){
        .infScroll h1 {
            font-size: 0.9375rem;
            letter-spacing: -0.0px;
        }
    }
    ```
    - 적용이 안되는데 개발자도구 style에서 보면 줄이 그어져있다. -> **`fs-4`를 보면 !important**가 명시되어있어서 **fs-4는 22px로 맞췄으니 더이상 필요없어 삭제**해주면 된다.
        - fs-4는 `먼저 header에서 import되는 main.css보다 나중에 적용`되고 덮어쓰기 위해 그렇다.
        ```html
        <h1 class="mb-1 text-body fw-bold">{{feed.title | truncate(50, true, '...') }}</h1>
        ```
      

3. subtitle은 sm에서 안보이게 하기 위해선
    - d-none for sm / d-md-block 을 매기면 된다.
    - **하지만 여기선 sm보다 더 작을 때 안보이고 `sm부터 보이게 d-sm-block`을 한다**
    ```html
    <h2 class="text-muted fs-6 d-none d-sm-block">{{feed.body | truncate(100, true, '...')  }}</h2>
    ```
   

### h1등 구체적 태그가 없는 text들(author, date)는 가장바깥 custom + 해당div custom class를 적용해서 반응형으로 만들기
1. 현재 반복되는 a태그의 커스텀 `infScroll`에 대해 h1 h2태그가 아닌 div태그로 작성된 author(category), date 글자들은 **직접 custom class를 만들어 특정해야한다.**
    - category -> `infScroll-category`
    - date -> `infScroll-date`
    ```html
    <div class="pb-2 text-body infScroll-category">{{feed.source.source_category.name}}</div>
    <h1 class="mb-1 text-body fw-bold">{{feed.title | truncate(50, true, '...') }}</h1>
    <h2 class="text-muted fs-6 d-none d-sm-block">{{feed.body | truncate(100, true, '...')  }}</h2>
    <div class="text-muted infScroll-date">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
    ```
   
2. 이제 2개의 선택자가 같은 크기로 줄어야하니 or개념인 콤마로 `.infScroll-author, infScroll-date` 미디어쿼리에서 sm일때 글자크기를 정의해준다.
    ```css
    @media only screen and (max-width: 768px){
        .infScroll h1 {
            font-size: 0.9375rem;
            letter-spacing: -0.0px;
        }
    
        .infScroll-category,
        .infScroll-date {
            font-size: 0.8125rem;
        }
    }
    ```
   

### 내부에서 친구들이 특정cusom class를 사용했다면, h1을 부모cutsom으로 공통h1태그를 특정할 필요 없어짐 -> custom class로 변경
- 기존
    ```html
    <a href="" class="text-decoration-none infScroll">
        <h1 class="mb-1 text-body fw-bold">
    ```
    ```css
    .infScroll h1 {
        font-size: 22px;
        letter-spacing: -0.6px;
    }
    
    @media only screen and (max-width: 768px){
        .infScroll h1 {
            font-size: 0.9375rem;
            letter-spacing: -0.0px;
        }
    
    ```
- 변경
    ```html
    <a href="" class="text-decoration-none">
        <h1 class="mb-1 text-body fw-bold infScroll-title">
    ```
    ```css
    .infScroll-title {
        font-size: 22px;
        letter-spacing: -0.6px;
    }
    
    @media only screen and (max-width: 768px){
        .infScroll-title {
            font-size: 0.9375rem;
            letter-spacing: -0.0px;
        }
    ```