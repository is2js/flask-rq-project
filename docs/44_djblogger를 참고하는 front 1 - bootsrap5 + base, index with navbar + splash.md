- 참고: https://www.youtube.com/watch?v=2yZHo_pgyMM&list=PLOLrQ9Pn6cawJ9CbY-o_kQC4GOWfhCFHq&index=29


### base/base.html + main/index.html 구성하기
1. templates에 `base/base.html` + `main/index.html`을 만든다.
    - 예시는 blog/index.html

2. base/base.html에는 bootstrap에서 css+js가 달린 CDN LINK의 코드를 복붙한다
3. main/index.html에서 base/base.html을 extends한다
    ```html
    {% extends "base/base.html" %}
    ```
4. main/index.html를 render_template하게 만든다
    ```python
    @main_bp.route('/')
    def index():
        return render_template('main/index.html')
    ```
   
5. base.html를 `block`들로 만든다.
    1. body태그안에 `template` block 만들어서 -> blog/index.html에서 `block 채워` 테스트
    2.  title의 context에 `title` block + `default 제목`
        - -> blog/index.html에서 `block 안채우고 default 테스트`
        - -> blog/index.html에서 `block 채우기`



### static/css/main.css 구성해서, base/base.html에 bootstrap CSS밑에 link태그 걸기
1. static폴더의 css/main.css를 생성하고 body에 background를 준다.
    - 장고와 달리 load static은 안됨.
    - link rel href=""에 url_for('static', filename='')으로 줘야한다.
    ```css
    body {
        background-color: blueviolet;
    }
    ```
    ```html
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css')}}">
    ```


### base/navbar.html 역시 공통되는 base이며, 필요에 따라 개별모듈(main/index.html)에서 include된다.(base.html에서 include X)
- 나는 base.html에 무조건 include되는 코드조각인 줄 알았는데, 여기서는 각 모듈에서 
    - extends base/base.html 이후 필요에 따라
    - **`(template) block 내부에서` include base/navbar.html을 한다.**

1. base폴더에 base/navbar.html을 생성하고
2. bootsrap페이지에서 코드를 복붙한다.
3. `main/index.html`에서 **template block 내부에서 text들보다 위쪽에 include를 따로 한다.**
    ```html
    {% extends "base/base.html" %}
    
    {% block title %} Index Page {% endblock title %}
    
    {% block template %}
        {% include "base/navbar.html" %}
    
    template block
    {% endblock template %}
    ```
   

4. 이제 main.css에 테스트용 배경을 지우고, 
    - base/base.html에서 body안에 h1태그를 지우고 template block + js코드만 남기고
    - main/index.html에서 template block안에 text를 지우고, include base/navbar.html만 남겨놓는다.


### navbar 수정하기
1. navbar태그의 맨 끝 배경을 결정하는 `bg-body-tertiary` or `bg-light`의 회색을 하얀색이 되도록 삭제한다.
2. `container-fluid` -> 최대로 뻗어서 표현된다. -> **어느 정도 양옆 간격을 가지도록 그냥 `container`로 변경한다**
2. navbar-brand, navbar-toggler(토글버튼)은 그대로 두고, 
3. **collapse되는 ul태그안의 `li들`만 모두 삭제한다.(메뉴 안씀)**
    - 그 뒤쪽 search용 form태그는 그대로 둔다.
    ```html
    <nav class="navbar navbar-expand-lg">
        <div class="container">
    
            <a class="navbar-brand" href="#">Navbar</a>
    
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent"
                    aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
    
            <div class="collapse navbar-collapse" id="navbarSupportedContent">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
    
                </ul>
                <form class="d-flex" role="search">
                    <input class="form-control me-2" type="search" placeholder="Search" aria-label="Search">
                    <button class="btn btn-outline-success" type="submit">Search</button>
                </form>
            </div>
        </div>
    </nav>
    ```
   

### Logo + main text의 지정해줄 google font 적용하기
1. language + bold까지 정하고 난 뒤 link태그가 아닌 style태그 + @import  url('') 을 선택해서 복사한 뒤, style태그내용물을 담는 `main.css`에 넣어준다.
    ```css
    @import url('https://fonts.googleapis.com/css2?family=Archivo:ital,wght@1,900&display=swap');
    ```
   
2. **그다음에 logo class에만 적용할 수 있게 font-family를 복사해와서 `.logo {}`에 지정해준다.**
    ```css
    @import url('https://fonts.googleapis.com/css2?family=Archivo:ital,wght@1,900&display=swap');
    
    .logo {
        font-family: 'Archivo', sans-serif;
    }
    ```
3. navbar.html의 a.navbar-brand태그에 `logo` class를 추가해준다.
    ```html
    <a class="navbar-brand logo" href="#">RQproject</a>
    ```
   

4. `fs-` cls로 글자크기를 조절해준다. + `.logo {}`에 `letter-spacing`을 -px로 줘서 간격을 좁혀준다.
    ```html
    <a class="navbar-brand logo fs-4" href="#">RQproject</a>
    ```
    ```css
    .logo {
        font-family: 'Archivo', sans-serif;
        letter-spacing: -1.5px;
    }
    ```
   

5. 이제 main text로 정할 font도 가져와야한다.
    - 나는 기존에 있던 font를 static/fonts/파일들로 두고 -> @font-face로 가져온 뒤
    - **자식태그안의 클래스로서 우선순위를 가지는`.logo`에는 영향을 못미치는 부모쪽 `html, body {}`에 걸어준다.**
    ```css
    @import url('https://fonts.googleapis.com/css2?family=Archivo:ital,wght@1,900&display=swap');
    
    @font-face {
        font-family: 'HallymR';
        src: url('../fonts/HallymR.eot');
        src: url('../fonts/HallymR.eot?#iefix') format('embedded-opentype'),
        url('../fonts/HallymR.woff') format('woff');
        font-weight: normal;
        font-style: normal;
    }
    
    .logo {
        font-family: 'Archivo', sans-serif;
        letter-spacing: -1.5px;
    }
    
    html, body{
        font-family: "HallymR", sans-serif;
    }
    ```
   

### main/index에만 포함(include)될 main/components/splash.html 작성하기
1. `main/components/splash.html`을 생성한다
    - 동일선상에 include될 base/navbar.html의 nav태그 아래 container로 시작하듯이. container로 시작한다
    ```html
    <div class="container">
        splash
    </div>
    ```
2. main/index.html에서  template block에 base/navbar.html 밑에 추가해놓고 코드작성을 시작한다
    ```html
    {% block template %}
        {% include "base/navbar.html" %}
        {% include "main/components/splash.html" %}
    {% endblock template %}
    ```
3. splash.html을 작성한다.
    1. container자체에 `border`속성을 주고 차지하는 부분을 확인한 뒤
    2. border -> `border-bottom`으로 변경하고 `border-2` `border-dark`로 굵기와 색을 준다.
    ```html
    <div class="container border-bottom border-1 border-dark">
        splash
    </div>
    ```
   
4. 우리는 container아래쪽이 아니라, 화면전체에 border-bottom을 주기 위해, container는 그대로 두고, 바깥쪽으로 border cls들을 옮긴다.
    ```html
    <div class="border-bottom border-1 border-dark">
        <div class="container">
            splash
        </div>
    </div>
    ```
   
5. 이제 글씨를 가장 큰 h1태그로 주되, 더 크게 만들기 위해 `display-` 속성을 준다.
    - font확인은 속성 > compute > font-famaily에서 보면 된다.
    ```html
    <div class="border-bottom border-1 border-dark">
        <div class="container">
            <h1 class="display-1">splash</h1>
        </div>
    </div>
    ```
   
6. 아래 설명 줄은 **다음줄로 넘어갈 수 있으므로**`p태그 with fs-`+ `lh-`(행간높이)를 기본으로 `text-muted`로 색을 준다. 
    ```html
    <div class="border-bottom border-1 border-dark">
        <div class="container">
            <h1 class="display-5">With RedisQueue</h1>
            <p class="fs-5 text-muted lh-2">
                Flask와 RedisQueue를 이용하여 다양한 비동기 작업들을 수행해봅니다.
            </p>
        </div>
    </div>
    ```
   
7. 이제 글씨 굵기를 결정할 것인데, `fw-` 중 `bold, bolder`가 너무 굵다고 판단되면
    - cutsom css로 font-weight를 직접 `fw-수치`로 만들어서 사용한다.
    - `fw-bolder`를 적용하고 compute를 보니 font-weight: 700으로 설정되어있어서 **`fw-500`을 `main.css`에 정의해서 사용해준다.**
    ```html
    <p class="fs-5 text-muted lh-2 fw-600">
        Flask와 RedisQueue를 이용하여 다양한 비동기 작업들을 수행해봅니다.
    </p>
    ```
    ```css
    .fw-600 {
        font-weight: 600;
    }
    ```
    - **때때로 custom class가 작동안되면, !important를 붙인 `font-weight: 600 !important;`로 작성하면 된다. 이경우는 잘 적용되서 놔둔다.**



8. **큰화면에서는 h1, p태그가 splash의 왼쪽편만 차지하게 하기 위해(왼쪽정렬처럼)**
    - flexbox로 구성된 row+2개 col조합의  grid를 사용해서, 절반을 나눈쪽만 h1, p태그가 차지하도록 container 아래 row>colx2를 적용한다.
    - `.row>.col*2`
    ```html
    <div class="border-bottom border-1 border-dark">
        <div class="container">
            <div class="row">
                <div class="col">
                    <h1 class="display-5">With RedisQueue</h1>
                    <p class="fs-5 text-muted lh-2 fw-600">
                        Flask와 RedisQueue를 이용하여 다양한 비동기 작업들을 수행하고, Database에 기록합니다.
                    </p>
                </div>
                <div class="col">
                </div>
            </div>
        </div>
    </div>
    ```
   
9. bootstrap `btn btn-dark` 버튼을 예시를 가져와서 p태그 아래 넣고 수정할 준비를 한다
    - `rounded-pill` 옵션을 추가하면 이쁜 버튼으로 바뀐다.
    - 굵기는 미리 정의해둔 p태그의 크기와 동일하도록 커스텀 `fw-600`을 사용한다. p태그와 `fs-`를 동일하게 주거나 약간 크게 준다.
    - 버튼글자와의 간격을 위해 `px-`를 사용해주고
    ```html
    <div class="col">
        <h1 class="display-3">RedisQueue</h1>
        <p class="fs-6 text-muted lh-2 fw-600">
            Flask와 RedisQueue를 이용하여 다양한 비동기 작업들을 수행하고, Database에 기록합니다.
        </p>
        <button type="button" class="btn btn-dark rounded-pill fw-600 fs-5 px-4">
            (예약) 메일 보내기
        </button>
    </div>
    ```
   
10. 이제 내용물이 차있는 `col` div에 패딩을 줄 건데, **화면 사이즈에 맞게 패딩을 준다**
    1. **모바일 sm일 때 패딩: `py-`**
    2. **중간이상부터의 패딩 : `py-md-더크게`**
    ```html
    <div class="col py-1 py-md-5">
    ```
    
11. 이제 p태그 <-> 아래 button사이에 간격을 padding으로 줄건데, 이왕이면 text에서 `pb-`으로 준다.
    ```html
    <h1 class="display-3">RQ프로젝트</h1>
    <p class="fs-5 text-muted lh-2 fw-600 pb-5">
    Flask와 RedisQueue를 이용하여 다양한 비동기 작업들을 수행하고, Database에 기록합니다.</br>
    </p>
    <button type="button" class="btn btn-dark rounded-pill fw-600 fs-5 px-4">
    (예약) 메일 보내기
    </button>
    ```
    

12. **이제 col2개로 자동 반땅 -> `아래col은 지우고` + col 1개의 `col-6`로 자동 반땅 확인 후**
    1. 모바일일 땐 전체 : `col-12`
    2. 커질 땐 반땅 : `col-md-6`으로 적용해본다.
    ```html
    <div class="row ">
        <div class="col-12 col-md-6 py-1 py-md-5">
            <h1 class="display-3">RQ프로젝트</h1>
            <p class="fs-5 text-muted lh-2 fw-600 pb-5">
                Flask와 RedisQueue를 이용하여 다양한 비동기 작업들을 수행하고, Database에 기록합니다.</br>
            </p>
            <button type="button" class="btn btn-dark rounded-pill fw-600 fs-5 px-4">
                (예약) 메일 보내기
            </button>
        </div>
    </div>
    ```
    


13. 이제 splash 내용물들을 가운데 정렬하기 위해 col에 `text-center`를 준다.
    - 이렇게 되면 커진화면에서는 반땅안에서만 가운데 정렬된다.
    - **flexbox(row)의 자식들(col)에 적용하는 옵션으로서 `text-사이즈-start`를 주면 왼쪽 정렬된다.**
    - 모바일부터 가운데 정렬: `text-center`
    - 커질때 왼쪽 정렬: `text-md-start`
    ```html
    <div class="row ">
    <div class="col-12 col-md-6 py-1 py-md-5 text-center text-md-start">
    ```