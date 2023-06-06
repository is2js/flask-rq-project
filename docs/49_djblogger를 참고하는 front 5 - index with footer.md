- 참고: https://www.youtube.com/watch?v=iJQy0tcKJ90&list=PLOLrQ9Pn6cawJ9CbY-o_kQC4GOWfhCFHq&index=38


1. footer도 재사용되므로 `base/`폴더에 `footer.html`로 만든다.
2. footer는 **footer태그 > ul.nav > (li.nav-item > a.nav-link)\*2들** 로 구성된다.
     - `footer>ul.nav>(li.nav-item>a.nav-link)*2`
     - 추가로 회색글씨(text-muted) + 굵기 fw-600(기존 커스텀)을 준다.
     ```html
    <footer>
        <ul class="nav">
            <li class="nav-item"><a href="" class="nav-link"></a></li>
            <li class="nav-item"><a href="" class="nav-link"></a></li>
        </ul>
    </footer>
    ```
   
3. **footer는 index.html의 category-cloud자리(col-4)에 include한다**
    ```html
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
                {% include "main/components/category-cloud.html" %}
                {% include "base/footer.html" %}
    
            </div>
    
        </div>
    </div>
    
    {% endblock template %}
    ```
   

4. footer의 글씨들은 특히 작아야하므로, `공통부모인 ul태그`에 custom 글자크기 `fs-12`를 0.75rem으로 만든다.
    - 여기선 main.css에 만든다. 공통으로 사용될 수 있기 때문.
    ```css
    .fs-12 {
        font-size: 0.75rem;
    }
    ```
    ```html
    <footer>
        <ul class="nav text-muted fw-600 fs-12">
            <li class="nav-item"><a href="" class="nav-link">푸터1</a></li>
            <li class="nav-item"><a href="" class="nav-link">푸터2</a></li>
        </ul>
    </footer>
    ```
   

5. footer에 대한 css를 `main.css`에서 줄 수 도 있지만, footer의 style은 공통 div사용없이 footer태그로만 적용되니 -> 자체적으로 style태그를 선언해서 사용한다.
    - **이렇게 하면 `footer.html이 include될때만 해당 css를 가져옴`**
    - **`include되는 요소에만 적용할 css`(글자크기 등 공통css (X))들은 include되는 html에 바로 style태그로 작성하자**
    - custom css를 줄 땐 custom class를 만들어서 주는데 **여기선 `모든 li.nav-link`에 대해 `공통css`를 한번에 주기 위해 `부모인 ul태그의 custom footer`의 모든 자식 `.nav-link`에 대해서 준다**
        - **.nav-link 자체가 padding이 너무 넓어서 `덮어쓰기로 패딩을 조절`한다.**
        - 다른 곳에 `.nav-link`가 있을 수 있으니 부모에 `.footer`를 만들어서 주는 것이다.
    - padding은 상->우->하->좌 순으로 주는데, **`이어지는 것들이므로 오른쪽` 10px간격, `다음줄로 넘어가니 아래`에 5px**준다.
    ```html
    <style>
         .nav-link{
            padding: 0 10px 5px 0;
        }
    </style>
    
    <footer>
        <ul class="nav text-muted fw-600 fs-12 footer">
            <li class="nav-item"><a href="" class="nav-link">푸터1</a></li>
            <li class="nav-item"><a href="" class="nav-link">푸터2</a></li>
        </ul>
    </footer>
    ```
   
6. 추가로 부모인 ul태그에 text-muted가 안먹는데, 자식들의 a태그에 색이 안먹힌다.
    - **자식들 a태그마다 text-decration-none + 매번 색을 줄 수 있지만, `한번에 부모에 글자색 + 부모의 color 상속`을 시키면 a태그에도 먹힌다.**
    ```html
    <style>
         .footer .nav-link{
            padding: 0 10px 5px 0;
        }
         .footer a {
             color: inherit;
         }
    </style>
    ```