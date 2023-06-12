- 참고: https://github1s.com/JuanLadeira/djblogger/blob/master/web/core/templates/blog/components/search-bar.html
- flask+htmx: https://www.youtube.com/watch?v=-qU3cfU35OE
    - github: https://github1s.com/SamEdwardes/htmx-python-course/blob/main/code/ch6_active_search/ch6_final_video_collector/views/videos.py

### 기존 search 정리
1. 현재 `index.html`의 search form / `3-col-template.html`의 search form -> search.html로 데이터를 전송한다
2. **하지만 나는, `3-col`을 상속해서 사용하지만, `search.html 내의 search form`은 live search를 하고 싶다.**
    - **3-col상의 search form에 block을 걸어서, 자식 중에 바꾸고 싶은 사람(search.html)에서 새롭게 블럭을 채우도록 하자.**
    - `3-col-template.html`
    ```html
    <div class="container" style="max-width:1500px!important;">
        <div class="row">
            <div class="col-navbar">{% block content_left %}{% endblock content_left %}</div>
            <div class="col-12 col-lg-8 pt-5 px-4 px-md-5">{% block content_mid %}{% endblock content_mid %}</div>
            <div class="d-none d-lg-block col-lg-3 pt-5">
                {% block search_form %}
                <form class="d-flex col-12  pb-5" role="search" action="{{url_for('main.feed_search') }}">
                    <input class="form-control rounded-pill" type="search" placeholder="search" aria-label="search"
                           name="search_text"
                    >
                </form>
                {% endblock search_form %}
                
                {% block content_right %}{% endblock content_right %}
            </div>
        </div>
    </div>
    ```
    - `search.html`에서는 search_form block을 새롭게 정의한다.
        - 일단 placeholder만 live search로 변경해서 확인해본다
    ```html
    {% block search_form %}
    <form class="d-flex col-12  pb-5" role="search" action="{{url_for('main.feed_search') }}">
        <input class="form-control rounded-pill" type="search" placeholder="Live Search" aria-label="search"
               name="search_text"
        >
    </form>
    {% endblock search_form %}
    
    {% block content_right %}
    {% include "main/components/category-cloud.html" %}
    {% include "base/footer.html" %}
    {% endblock content_right %}
    ```
   

3. form의 `input`에 htmx를 적용하여 **key를 up떼고 몇ms있다가 바로 요청보내도록 한다.**
    - **기존에는 `form의 action=`으로 `input의 name + value`를 get form에 query param으로 보냈지만**
        ```html
        {% block search_form %}
        <form class="d-flex col-12  pb-5" role="search" action="{{url_for('main.feed_search') }}">
        <input class="form-control rounded-pill" type="search" placeholder="search" aria-label="search"
        name="search_text"
        >
        </form>
        {% endblock search_form %}
        ```
    - **live search를 위해서라면 `form action=`은 사라져야한다. `form으로 화면이 넘어가면 안된다.`**
    - **`input`태그에 `hx-get=`으로 route에게 신호를 보내서 템플릿 + 데이터를 받아야한다.**
    - **`input`태그에 `hx-trigger=`로 keyboard움직임으로 요청이 보내져야한다.**
    - 이 때, name, value가 query param으로 날아가는 것은 똑같은데, **search.html로 진입시 들어오는 `search_text`를 `{{ request.args.search_text or ''}}`를 통해 `value=`에 미리 입력해둔다.**
    - **`page=`는 안보내는데, `live search시 page는 무조건 첫번째여야하기 때문이다.` route에서 default 1로 잡게 한다.**
        - 하지만 route에서 htmx요청에 대해서는 page를 받아줘야한다. components는 page를 사용하기 때문에, page + 1을 무한스크롤시 보낸다.
    ```html
    {% block search_form %}
    <form class="d-flex col-12  pb-5" role="search">
        <input class="form-control rounded-pill" type="search" placeholder="Live Search" aria-label="search"
               name="search_text"
               value="{{ request.args.search_text or '' }}"
               hx-get="{{ url_for('main.feed_search')}}"
               hx-trigger="keyup changed delay:250ms"
        >
    </form>
    {% endblock search_form %}
    ```
    - **여기까지만 하면, terminal에 실시간 요청이 전해진다.**
4. **추가로 `hx-push-url="true"`을 통해, **요청되는 hmtx의 route주소를 현재 페이지의 url에 반영되게 한다.**
    - 이게 반영이 되어야 **components 내부 `if has_next의 무한스크롤 요청시, 현재url의 search_text를 가져올 수 있게 된다.`**
    - `feed-list-elements-search.html`
        ```html
        {% if has_next %}
        <div class="text-center htmx-settling"
             hx-trigger="revealed"
             hx-get="{{ url_for('main.feed_search', page=page +1, search_text=request.args.search_text )}}"
             hx-swap="outerHTML"
        >
            <img src="/static/image/htmx/bars.svg" width="120px"
             class="htmx-indicator"
            />
        </div>
        ```
    ```html
    {% block search_form %}
    <form class="d-flex col-12  pb-5" role="search">
        <input class="form-control rounded-pill" type="search" placeholder="Live Search" aria-label="search"
               name="search_text"
               value="{{ request.args.search_text or '' }}"
               hx-get="{{ url_for('main.feed_search')}}"
               hx-trigger="keyup changed delay:250ms"
               hx-push-url="true"
        >
    </form>
    {% endblock search_form %}
    ```
   
5. **기본적으로 요청결과는 `hx-swap="innerHTML"`이 적용되고, `hx-target`을 정해서 해당 target의 내부를 replace하게 한다.**
    - 그러므로 live search 결과를 받아줄 `div#search_results`를  components include하는 곳에 부모로서 씌워준다.
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
    
        <div class id="search-results">
            {% include "main/components/feed-list-elements-search.html" %}
        </div>
    </div>
    {% endblock content_mid %}
    ```
    - 이제 `hx-target`을 `#search_results`로 css선택자처럼 지정해준다.
    ```html
    {% block search_form %}
    <form class="d-flex col-12  pb-5" role="search">
        <input class="form-control rounded-pill" type="search" placeholder="Live Search" aria-label="search"
               name="search_text"
               value="{{ request.args.search_text or '' }}"
               hx-get="{{ url_for('main.feed_search')}}"
               hx-trigger="keyup changed delay:250ms"
               hx-push-url="true"
               hx-target="#search-results"
               hx-swap="innerHTML"
        >
    </form>
    {% endblock search_form %}
    ```
   

6. **추가로 더이상 데이터가 없습니다는, page가 1인 첫 요청결과에서는 제외시켜준다?!**
    - page > 1이상일때, has_next가 없다면, `더이상 데이터가 없습니다` 표시
    - page == 1이인데, has_next가 없다면, `데이터가 존재하지 않습니다` 표시
    ```html
    {% if has_next %}
    <div class="text-center htmx-settling"
         hx-trigger="revealed"
         hx-get="{{ url_for('main.feed_search', page=page +1, search_text=request.args.search_text )}}"
         hx-swap="outerHTML"
    >
        <img src="/static/image/htmx/bars.svg" width="120px"
         class="htmx-indicator"
        />
    </div>
    {% else %}
        <div class="text-center">
        {% if page == 1 %}
            <h5> 데이터가 존재하지 않습니다. </h5>
        {% elif page > 1 %}
            <h5> 더이상 데이터가 없습니다. </h5>
        {% endif %}
        </div>
    {% endif %}
    ```
    - 모든 feed-list-elements-x에 적용해준다.    