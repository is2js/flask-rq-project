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
    - 3-col을 만들라면 row + col3개로 만들어야한다.
        - `.row>.col*3`
        - **나중에는 col대신 nav가 들어가면서 바뀔 예정**
    ```html
    {% extends "base/base.html" %}
    
    {% block template %}
    <div class="container" style="max-width:1500px!important">
        <div class="row">
            <div class="col"></div>
            <div class="col"></div>
            <div class="col"></div>
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
            <div class="col">{% block content_left %}{% endblock content_left %}</div>
            <div class="col">{% block content_mid %}{% endblock content_mid %}</div>
            <div class="col">{% block content_right %}{% endblock content_right %}</div>
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
   


### 3-col-template에 horizontal nav 만들기
