- 현재까지 sm/lg시 content_mid에 있는 feed의 내용들이 뭉쳐져있고 여백도 없다.
- 또한, 축소될 때 text가 줄지 않는다.(scale down) -> **bootstrap사용시 `h1 ~ h4 4태그` 까지는 자동으로 scale down이 적용되는 듯.**
    ```css
    .h1, h1 {
        font-size: calc(1.375rem + 1.5vw);
    }
    ```
- 또한, search form이나 관련 feed도 안나와있음.

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

1. **커질 때 여백을 만드는 방법은 `style="max-width"`를 lg breakpoint로 지정하여 `더 커지면 margin이 생기는데` + `mx-auto`를 통해 가운데 모이게 하는 것이다**
    - 이 때, lg breakpoint 보다 작아질 때 위쪽에 horizontal로 올라가는 navbar의 크기에 맞추기 위해
        - container의 custom max-width인 720px보다 더 작게 준다.
        - brand logo의 시작위치를 위해 양쪽 margin도 빼서 대충 계산한다. -> 680px을 하니, lg보다 작아질 때 나타나는 위족 logo랑 비슷하게 움직인다.
    ```html
    <div class="mx-auto" style="max-width: 680px">
        <div>{{feed.source.source_category.name}} > {{feed.source.name}}</div>
        <div>{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
        <h1>{{feed.title}}</h1>
        <h2>원본링크: {{feed.url}}</h2>
        <h5>{{feed.body}}</h5>
    </div>
    ```
2. content_mid block을 채우는 글자들을 `div`로 한번 감싸서 `.custom class 공통태그(h1, h2)`형태로  **`알려진 공통태그들을 꾸밀 수 있게 custom 태그로 감싼다`**
    - **h1, h2는 다른데서 공통되지만, 부모에 커스텀class를 줘서 꾸밀 수 있다.** 
    - 진하기는 커스텀css가 필요없이 `fw-bold`로 가고, 자간을 `.single-feed h1`으로 주면 된다.
    ```html
    {% block content_mid %}
    <style>
        .single-feed h1 {
            letter-spacing: -0.6px;
        }
    </style>
    
    <div class="single-feed">
        <div>{{feed.source.source_category.name}} > {{feed.source.name}}</div>
        <div>{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
    
        <h1 class="fw-bold display-3">{{feed.title}}</h1>
        <h2>원본링크: {{feed.url}}</h2>
        {{feed.body}}
    </div>
    
    {% endblock content_mid %}
    ```
    - 아래 와 간격을 주기 위해 `pb-2`로 해결한다.

3. 이제 div로 담긴 카테고리 + 시간은 회색으로 / subtitle(링크)는 회색 + h2태그지만 글자크기 조절을 `fs-4` 및 아래 본문과의 여백을 `pb-4`로 준다
    - **`fs-x`도 자동으로 크기조절이 들어가있다. h2보다 더 작은 글자로 준다.**
    - `h2.fs-4`는 h3보다 더 작다.
    ```html
    <div class="single-feed mx-auto" style="max-width: 680px">
        <div class="text-muted">{{feed.source.source_category.name}} > {{feed.source.name}}</div>
        <div class="text-muted">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
    
        <h1 class="fw-bold pb-2">{{feed.title}}</h1>
        <h3 class="text-muted pb-4 fs-4">원본링크: {{feed.url}}</h3>
        {{feed.body}}
    </div>
    ```
       

4. **본문 `body`는 일단 비워둔다. `markdown이 적용되서 보여야한다.`**


### markdown 필터 생성 후 view에서 적용하기
1. `Markdown` 패키지 인스톨
    - 나는 이전에 markdown2를 설치해놨었음.
2. 최신글의 제일 앞에 `# 제목` + ctrl-Enter로 맨앞에 추가입력하여 확인하기
    - `# ㅋㅋㅋㅋ [민족의학신문`
3. **templates > filters에 `markdown_processing.py`를 추가한 뒤 내부 `def markdown(value)` 필터 메서드 생성 후 init에 걸어주기**
    ```python
    import markdown2 as md
    
    def markdown(value):
        return md.markdown(value)
    ```
    ```python
    from .remain_from_now import remain_from_now
    from .markdown_processing import markdown
    ```
    ```python
    def create_app():
        app.jinja_env.filters["remain_from_now"] = remain_from_now
        app.jinja_env.filters["markdown"] = markdown
    
        return app
    ```
4. **markdownfilter는 `# xxxx`를 `<h1>ㅋㅋㅋㅋ</h1>`의 html태그로 변경해준다**
    ```html
    {{feed.body | markdown}}
    ```
5. `| safe`필터까지 추가해야 화면에서 html태그가 보이게 된다.
    ```html
    {{feed.body | markdown | safe}}
    ```
   



### 본문용 글자태그 css추가하기
- 현재 `single-feed` cls안에 `title의 h1태그`는 다 똑같이 적용되므로 **자식으로서 `body에 자식div` + `커스텀 클래스`를 추가하여 -> `h1`태그에 다르게 적용되게 해야한다.**
1. body에 `div.feed-body`를 씌워 `div.single-feed`의  자식개념으로 넣는다.
    ```html
    <style>
        .single-feed h1 {
            letter-spacing: -0.6px;
        }
    </style>
    <div class="single-feed mx-auto" style="max-width: 680px">
        <div class="text-muted">{{feed.source.source_category.name}} > {{feed.source.name}}</div>
        <div class="text-muted">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
    
        <h1 class="fw-bold pb-2">{{feed.title}}</h1>
        <h3 class="text-muted pb-4 fs-4">원본링크: {{feed.url}}</h3>
        <div class="feed-body">
            {{feed.body | markdown | safe}}
        </div>
    </div>
    ```
   
2. **현재 `{{feed.body | markdown | safe}}` 내부에 이미 `# 제목` -> `<h1>태그`가 들어가 있으니, `.feed-body h1`으로 css를 주면 된다.**
    - 내부h1태그라 반응형 `fs-x`를 못주지만, 본문의 글자크기는 변할필요가 없을 것 같아 조금 작은 사이즈로 준다.
    - title은 h1태그가 원래 37px정도 되더라. `본문의 h1태그는 24px + 진하게` 적용되게 한다.
    ```html
    <style>
        .single-feed h1 {
            letter-spacing: -0.6px;
        }
    
        .feed-body h1 {
            font-size: 24px;
            font-weight: bold;
        }
    </style>
    ```
   
2. **마크다운으로 변환된 글자들은 태부분 `p태그`속에 들어가있다. `.feed-body p`로 글자체 + 글자크기를 수정해주자.**
3. google font에서 import로서 가져와 **`main.css`**에 등록해놓고
    ```css
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600&display=swap');
    ```
   
4. family=에 붙은 문자열만 `'abc'` 그대로 입혀주면 된다.
    - `+`그래도 넣어줘도 적용된다.
    ```html
    <style>
        .single-feed h1 {
            letter-spacing: -0.6px;
        }
    
        .feed-body h1 {
            font-size: 24px;
            font-weight: bold;
        }
        .feed-body p {
            font-family: 'Noto+Serif+KR';
        }
    </style>
    ```
   
5. import 에러대비 기본글자체도 같이 넣어준다.
    ```css
    .feed-body p {
            font-family: 'Noto+Serif+KR', sans-serif;
        }
    ```
   

6. **p태그는 기본적으로`line-height:`도 같이 준다.**
    - 추가로 글자크기 + 자간도 같이 준다.
    ```css
    .feed-body p {
        font-family: 'Noto+Serif+KR', sans-serif;
        font-size: 1.0625rem;
        line-height: 32px;
        letter-spacing: 0.2px;
    }
    ```
   
7. 추가로 위쪽 날짜 <-> title간의 간격을 `pb-3`로 준다.
    ```html
    <div class="single-feed mx-auto" style="max-width: 680px">
        <div class="text-muted">{{feed.source.source_category.name}} > {{feed.source.name}}</div>
        <div class="text-muted pb-3">{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
        <h1 class="fw-bold pb-2">{{feed.title}}</h1>
        <h3 class="text-muted pb-4 fs-4">원본링크: {{feed.url}}</h3>
        <div class="feed-body">
            {{feed.body | markdown | safe}}
        </div>
    </div>
    ```


### 3-col에서 content_mid의 전체를 패딩으로 위에서 약간 떨어뜨려놓기
1. sm일때는 위에 horizontal navbar가 있지만, lg일때 `content_mid`가 상단과 너무 붙어있다.
    - sm일때부터 그냥 `pt-5`으로 상단과 떨어뜨려놓는다.
2. 좌측과의 간격도 준다. 양측으로 `px-4`로 준다
    - md부터는 1칸 더줘서 `px-md-5`로 준다.
3. 