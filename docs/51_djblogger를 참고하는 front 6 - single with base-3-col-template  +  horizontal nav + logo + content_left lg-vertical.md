### base/3-col-template.html 작성하기 
1. 3단계 column template은 main/single.html뿐만 아니라 다른데서도 사용될 수 있기 때문에, main/index.html처럼 base/base.html을 상속할 예정이지만, `base/3-col-template.html`에 만든다.
    - base폴더에는 공통요소를 담는 `base.html`이 각 몯류별 `extends`(main/index.html)에 제공되지만
        - 또한, base.html을 `extends`하면서, 동시에 `extends`(main/single.html)로 제공될 `3-col-template.html`도 제공한다. 
        - 그외 `include`로 제공될 `navbar.html, footer.html`들도 있다.

2. 일단 **`include될 html`이 아니라면, `base를 extends해서 시작하는 html`로 시작해서 `template block을 채우면서 시작`한다.**
    ```html
    {% extends "base/base.html" %}
   
    {% block template %}
 
    {% endblock template %}
    ```
   
3. base.html extends로 시작했지만, **직접 render될 html이 아니라면, `render되는 html == extends + block채우기`를 위해 block을 내주는 html이어야한다.**
    - base/base.html - `template block` 
        - extends후 block base/3-col-template.html `content_left, _mid, _right block`
             - extends후 block채우기 single.html
        - **django와 달리 block이름에 `-` 하이픈이 들어가면 안된다.**
    - **block을 내어주기 전에 틀을 `block을 내어줄 틀`을 잡아야한다.**
    - **일단 `일반 div.container`는 양측으로 짤려있기 때문에, 가로로 가득채워서 3-col을 만들고 싶은데, 너무 큰 화면을 다채우면 안돼니 직접 `가능하다면 최대 width 1500px까지는 차지하고 싶다`를 직접 지정해서 넓혀줘야한다.**
    ```html
    {% extends "base/base.html" %}
    
    {% block template %}
    <div class="container" style="max-width:1500px!important">
    
    </div>
    {% endblock template %}
    ```
    - 3-col을 만들라면 `row`아래 `3개의 div`를 만든다. **`row`는 `flex`로서 하위아이템들을 inline-block?처럼 자기content영역만큼만 차지하게 만든다.**
        - `.row>.div*3`
        - **`col class주는 것은 나중에` 한다. `주는 순간 horizontal로 먼저 화면을 먼저 만드는게 불가능`해진다.**
    ```html
    {% extends "base/base.html" %}
    
    {% block template %}
    <div class="container" style="max-width:1500px!important">
        <div class="row">
            <div class=""></div>
            <div class=""></div>
            <div class=""></div>
        </div>
    </div>
    {% endblock template %}
    ```
    - 3개의 block을 내어준다.
    ```html
    {% extends "base/base.html" %}
    
    {% block template %}
    <div class="container" style="max-width:1500px!important">
        <div class="row">
            <div class="">{% block content_left %}{% endblock content_left %}</div>
            <div class="">{% block content_mid %}{% endblock content_mid %}</div>
            <div class="">{% block content_right %}{% endblock content_right %}</div>
        </div>
    </div>
    {% endblock template %}
    ```
   

4. 이제 render되는 html인 single.html에서 3-col-template.html을 extends 후 3-col block을 채운다.
    - main/singe.html
    ```html
    {% extends "base/3-col-template.html" %}
    
    {% block content_mid %}
    <div>{{feed.source.source_category.name}} > {{feed.source.name}} </div>
    <div>{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
    
    <h1>{{feed.title}}</h1>
    <h2>원본링크: {{feed.url}}</h2>
    {{feed.body}}
    {% endblock content_mid %}
    ```
   


### single.html의 content_left block채울 때 사용되는, 공통으로서 include될 horizontal nav 만들기
- `col로 수직 3-col 세우기 전`에 **가로로 나열되는 상황인 horizontal nav부터 만든다..**
    - 현재 left block이 row>col로 되어있으므로 서있는 상태다.

- base > 3-col > single - `content_left` / content_mid / content_right block 중 
    - left를 render되는 single.html에서 채원야하는데 

1. 3-col-template > single.html에서 채워야하는 `left block`에는 `nav.navbar`가 block을 채워야하는데 `nav자체는 공통`으로 쓰일 수 있으니 `base/navbar-secondary.html`를 만든다.
    - nav태그는 기본적으로 `.navbar` class를 줘서 **자신은 static이 아닌 relative +  `자식들을 flex + 자식들 가운데정렬`을 기본으로 한다.**
    ```css
    navbar{position:relative;display:flex;flex-wrap:wrap;align-items:center;
    ```
    - `navbar-expand-lg` class를 주지 않으면 **계속 햄버거 상태라서 `필수 옵션`이다.**
    - **navbar 자체에 자식들 가운데 정렬`align-items:center;`가 지정되어있으므로 `자식들 왼쪽정렬`시 `align-items-start`도 왼쪽정렬 필수옵션이다.**
        - 기존 navbar.html은 가운데정렬될 자식들X  
        - 자식은 기본적으로 `ul.navbar-nav`안에 `li`로 채워진다. 이전에는 `자식들없이 ul태그에 me-auto로 가득채워서` search폼을 오른쪽으로 밀어버렸다.
    - 또한, 전체적으로 그냥div안에 있으므로 `사이트전체의 여백을 위해 nav태그바로 밑에 container를 씌우고 작성`하게 된다.
    ```html
    <nav class="navbar navbar-expand-lg align-items-start">
        <div class="container">
            ㅇ
        </div>
    </nav>
    ```
   

2. 기본틀만 `main/single.html`의 content_left block에 include로 채워서 보자
    - include시킨다
    ```html
    {% extends "base/3-col-template.html" %}
    
    {% block content_left %}
        {% include "base/navbar-secondary.html" %}
    {% endblock content_left %}
    
    {% block content_mid %}
        <div>{{feed.source.source_category.name}} > {{feed.source.name}} </div>
        <div>{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
        
        <h1>{{feed.title}}</h1>
        <h2>원본링크: {{feed.url}}</h2>
        {{feed.body}}
    {% endblock content_mid %}
    ```
   


3. 이제 화면을 보고 **부모영역에서, 자신의 원래위치보다 스크롤이 내려간다면, 상단에 고정되어 따라가는 `sticky-top`을 container에 적용**해보자.
    - **가로navbar라면 fixed로 충분할텐데, `작은화면에선 세로로 세워지며, 세로의 긴 col안에서 스크롤 될 때 nav요소가 따라가도록`하기 위함이다.**
    - 이 때, 부모영역자체(nav.navbar)가 자식(div.container.sticky-top)과 비슷하면, 작동을 안하므로 임시로 부모에 `min-height:200px`을 준상태다.
    ```html
    <nav class="navbar navbar-expand-lg align-items-start " style="min-height: 200px;">
        <div class="container sticky-top">
            ㅇ
        </div>
    </nav>
    ```
    - 화면을 보면, 자식요소의 `ㅇ`이 부모인 nav영역안에서 스크롤내릴 때 자신보다 내려가면 따라가게 된다.
        - 참고로 nav.navbar는 position:relative이므로 sticky의 기준부모가 될 것이다.

    - **추가로, navbar역시 include시키고 있는 content_left에 대해서 따라가도록 stick-top을 줘놓는다?**
    ```html
    <nav class="navbar navbar-expand-lg align-items-start sticky-top">
        <div class="container sticky-top">
            ㅇ
        </div>
    </nav>
    ```
                    

### css로 nav-secondary의 brand만들기

1. 클릭이 되어야하므로 a태그로 navbar-brand css를 입혀야한다. `a.navbar-brand`로 만든다.(저번 navbar와 동일)
    - 이 때, `href="/"`로 걸면된다.
    ```html
    <nav class="navbar navbar-expand-lg align-items-start sticky-top">
        <div class="container sticky-top">
            <a href="/" class="navbar-brand"></a>
        </div>
    </nav>
    ```
   
2. 이제 로고를 2개 영역으로 그릴건데 **id를 배정해서 css `#` 선택자로 작성한다.**
    - `#sm-logo-out>#sm-logo-in`
    - **바로 style태그를 통해 css를 작성해버린다.**
    - **my) `include`될 놈이 공통속성이 아니면 바로 style태그로 작성. `footer.html, navbar-secondary.html`**
    ```html
    <style>
        #sm-logo-out {
        }
    </style>
    
    <nav class="navbar navbar-expand-lg align-items-start sticky-top">
        <div class="container sticky-top">
            <a href="/" class="navbar-brand">
                <div id="sm-logo-out">
                    <div id="sm-logo-in">
        
                    </div>
                </div>
            </a>
        </div>
    </nav>
    ```
   

3. my) icon처럼 위치 **부모를 기준**상세이동을 할 예정인 친구들은 **`position:relative`를 주고, 움직일 준비를 한다.**
    - **부모의 `높이의 중간값`만큼 이동시키려면 `top:50%`를 주면 된다.**
        - 부모기준 50%만큼 이동은 `transform: translateY(-50%);`도 가능하다고 한다.
    - 검은색 배경에 38x38px로 만들 것이다.
    ```css
    <style>
        #sm-logo-out {
            position: relative;
            background: #000;
            width: 38px;
            height: 38px;
        }
    </style>
    
    <nav class="navbar navbar-expand-lg align-items-start sticky-top">
        <div class="container sticky-top">
            <a href="/" class="navbar-brand">
                <div id="sm-logo-out">
                    <div id="sm-logo-in">
                        sm-logo
                    </div>
                </div>
            </a>
        </div>
    </nav>
    ```
   
4. 안족영역에 네모를 하나더 그릴 것이다. 역시위치 `부모기준 상세이동` 대상이라 `position:relative`로 주고 간다.
    - 12x12의 흰색네모이며 **부모(검은색네모)의 높이는 18%위치, 왼쪽에서는 `시작점을 절반위치로` 가져간다. 위치시키자.**
    ```css
    <style>
        #sm-logo-out {
            position: relative;
            top: 50%;
            background: #000;
            width: 38px;
            height: 38px;
        }
    
        #sm-logo-in {
            position: relative;
            top: 18%;
            left: 50%;
            background: #fff;
            width: 12px;
            height: 12px;
        }
    </style>
    ```
   

5. 이제  nav.navbar 자체의 여백을 설정한다.
    - 패딩 위아래1, 패딩위쪽은 lg일때(세로로 설 예정) 4추가, 
    - container는 위아래2, 좌우4 패딩를 추가한다.커질때(세로로 설 예정)는 **`기본패딩 상하0 좌우12를 씹기`위해 좌우패딩0인 `px-lg-0`을 준다.
    ```html
    <nav class="navbar navbar-expand-lg align-items-start sticky-top py-1 pt-lg-4">
        <div class="container  sticky-top py-2 px-4 px-lg-0">
            <a href="/" class="navbar-brand">
                <div id="sm-logo-out">
                    <div id="sm-logo-in">
                        sm-logo
                    </div>
                </div>
            </a>
        </div>
    </nav>
    ```
   

### 3-col의 content_left부분을 lg전까지는 vertical(col)로, lg부턴 vertical로

1. **일단 horizontal navbar(순서상 위쪽div) `content_left block을 담는 div`를 `lg시 세로`로 세워야한다.**
    1. **`.col-navbar`라는 class를 부여한 뒤, media쿼리를 통해, `lg breakpoint`(992px)을 `min-width:992px`로 잡아 `lg상태`를 맞춰놓고**
        ```html
        <style>
            @media only screen and (min-width: 992px){
                .col-navbar {
                    
                }
            }
        </style>
        <div class="container" style="max-width:1500px!important;">
            <div class="row">
                <div class="col-navbar">{% block content_left %}{% endblock content_left %}</div>
        ```
   2. **현재요소를 flex-item으로 만드는 `display:flex;` + `flex:` 속성을 통해 `grow 0`(부모 flex-conatiner에 따라 늘어나질 않음), `shrink 0`(부모가 줄어도 나는 축소 하지않음) `80px 고정값`으로 item내부 컨텐츠크기 시작크기**를 지정한다.
       - 이렇게 지정하면 flex: 1 1 auto와 반대값으로 **부모와 상관없이 고정된크기로 flex-item이 고정됨.**
        ```html
        <style>
            @media only screen and (min-width: 992px){
                .col-navbar {
                    display: flex;
                    flex: 0 0 80px;
                }
            }
        </style>
        ```
      
2. 80px로 고정만된 flex-item일 뿐, vertical로 선 상태가 아니다.  **div를 화면을 꽉찬 col로 만들기 위해 `height: 100vh;`을 준다.**
    - **`height: 100vh;`을 줘서, 화면크기만큼 해당 아이템이 차지하게 된다 -> 내부 navbar + logo는 sticky-top으로 붙어있게 된다.**
    - **추가로 border를 오른쪽에만 주고, item내부 요소들을 `justify-content:center;`로 가운데 정렬시킨다.**
    ```html
    <style>
     @media only screen and (min-width: 992px){
         .col-navbar {
             /*크기 가로 80px 고정*/
             display: flex;
             flex: 0 0 80px;
            /* 가로 가운데정렬  */
            justify-content: center;
             /* div를 -> vertical용 col을 만듦 */
             height: 100vh;
             border-right: 1px solid #dee2e6;
         }
     }
    </style>
    ```
    - **content_left에 대해서 lg전까지는 horizotanl <-> lg부터는 80px을 차지하는 flex-item이 되도록 했다.**

3. 이제 sm시 horizontal / lg시 verical 한 content_left에 대해 **`mid와 right`를 조작 해주어야한다.**
    - sm
        - mid는 sm시 row에 대해 전체(`col-12`)를 차지하게 한다 -> **left는 horizontal로 위에 떠있다.** 
        - right는 sm시 `d-none`으로 안보인다
    - lg
        - mid lg시 -> **left가 flex-item으로서 80px차지하고 있으니 col-lg-1이라고 간주**하고 col-lg-11 중 `col-lg-8`만 가져간다 (right에게 lg시 col-3양보)
            - **row안에서 `col아닌 flex div`(content_left)가 먼저 있을 때, `col-12 or col-lg-12`등 `12`만 아니면 `앞에 flex div`에 붙는다.** 
        - right lg시 -> 일단 보이게 `d-lg-block`부터 주고 나머지 `col-3`을 가져간다.

4. 확인해보니 brand a태그에 margin이 붙어서 `m-0`으로 삭제한다.
    ```html
    <!-- app/templates/base/navbar-secondary.html-->
    <nav class="navbar navbar-expand-lg align-items-start sticky-top py-1 pt-lg-4">
        <div class="container  sticky-top py-2 px-4 px-lg-0">
            <a href="/" class="navbar-brand m-0">
    ```
   

### md -> sm로 넘어갈 때 .container에 의해 max-width가 잡혀 좁아져 logo가 이동하는 문제 해결
1. container와 container-sm은 **미디어쿼리가 `md->sm진입시 max-width:580px`가 걸려버려서, 내용물이 다시 가운데로 모여버린다.**
2. **`.container대신 .container-md`를 줘서, `md이상부터 container가 적용되어 가운데로 안모이게`할 수 도 있고**
3. **`.container-fluid`를 줘서 항상 width 100%를 유지할 수도 있다.**
4. **제일 좋은 것은 `적용되는 미디어쿼리 복사` -> `해당시만 width 100%`로 직접 주면 된다.**
    1. 줄이다가 튀는 곳에서 멈쳐서 미디어쿼리를 확인하고 복사한다.
        ```css
        @media (min-width: 576px)
        .container, .container-sm {
            max-width: 540px;
        }
        ```
    2. **`최소 sm(576)부터(min)` 이미 540으로 제한되고 있다. 하지만 나는 `md이하(768)부터(max)`도 md이상처럼 `max-width 100%`를 주고 싶다**
        ```css
            @media only screen and (max-width: 768px) {
                .container, .container-sm {
                    max-width: 100%;
                }
            }
        ```
        