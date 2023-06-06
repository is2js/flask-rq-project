- 참고: https://www.youtube.com/watch?v=twhz1P5SRfw

### utils-slugify 정의 후, db.event.listen에 Feed.title + 콜백메서드를 "set"시 listen -> target.slug채우기
1. models패키지에 utils.py를 만들고 re를 이용해 value가 오면 slug로 만들어주는 `slugfy`메서드를 만든다.
    - 정규표현식 `r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ-]'`은 `^`아닌것을 골라내는데 `\w`알파벳, `\s`공백(공백은 모아뒀다가 하이픈`-`으로 만들 예정), `가-힣ㄱ-ㅎㅏ-ㅣ`한글, `-` 하이픈을 제외한 것들을 모두 제거한다.
    - 제거한 뒤 양옆의 공백은 .strip()으로 제거하고 .lower()로 소문자를 만든다.
    - 이제 남은 `-` 혹은 ` `공백을 `-`하이픈으로 대체한다.
    ```python
    # app/models/utils.py
    import re
    
    def slugify(value):
        value = re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ-]', '', value).strip().lower()
        value = re.sub(r'[-\s]+', '-', value)
        return value
    
    ```
   
2. models/init.py에 올리되 **모델의 staticmethod에서 사용할 것이므로 `유틸을 가장 먼저 import하여 사용예정처`(from .sources import 모델들)`보다 먼저 import되게한다`**
    - 안그러면, 사용예정처가 먼저 import해서 사용 -> 그 이후 import되어서, 순환에러 뜬다.
    ```python
    from .utils import slugify
    from .tasks import Task, Notification, Message
    from .sources import Feed, Source, SourceCategory
    ```
   
3. **이제 Feed 모델에 input->output의 콜백메서드로서 `@staticmethod`로 slug 생성 메서드 `generate_slug`를 정의한다.**
    - **`title과 동일한 slug필드`도 같이 만들어준다. 검색용으로서(`unique=True` or index=True)를 추가해준다.**
    - **이 때, `sqlalchemy.event 중 "set"시 요구되는 callback메서드형태로 인자`(`target`-모델obj, `value`-새값, `old_value`-기존값, `initiator`)를 만든다.**
    - target: feed 데이터 object
    - value: set할 데이터(Feed.generate_slug)
    - old_value: 기존값(없음)
    ```python
    class Feed(BaseModel):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(180), nullable=False)
        slug = db.Column(db.String(180), nullable=False, unique=True)
        #...
        @staticmethod
        def generate_slug(target, value, old_value, initiator):
            if value and (not target.slug or value != old_value):
                target.slug = slugify(value)
    ```
   
4. 이제 전역공간에 event를 선언해준다. db는 sqlalchemy import본임.
    - 옵션을 "`set`"으로 줘서 insert`시` 작동하게 한다.
    - `Feed.title`을 `listen의 target`으로 넣어주면 ->  `"set"`이 감지시 `콜백메서드내 target은 해당데이터obj`가 되는 듯하다 
    ```python
    db.event.listen(Feed.title, 'set', Feed.generate_slug, retval=False)
    ```
    - 과거에는 아래와 같이 engine을 'connect'시 작동하게 만들었다
        - `engine을 listen target`으로 넣어주면, ->  `콜백메서드에선 target이 connection`으로 잡히나보다., 
    ```python
    #### sqlite 인 경우, qeuery 날릴 때마다, 아래 문장을 execute해야, cascade가 정상작동한다
    # 1) many에서 ondelete='cascade' -> # 2) one에서 passive_deletes=True 로만 작동할 수있게 매번 제약조건 날려준다
    def _fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute('pragma foreign_keys=ON')

    if self.__connection_string.startswith('sqlite'):
        event.listen(engine, 'connect', _fk_pragma_on_connect)
    ```
    - target이 어떻게 obj가 잡히는지 의문이긴 함. 알아서 내부에서 cls를 잡아내는 듯?


5. **이제 feed 테이블을 지우고, 재시작해서 데이터를 새로얻을 때, slug도 채워지는지 확인한다.**
    - **이 때, `scheduler를 강제 cancel`시켜야 끝난 상태로 간주하고 돌아간다. 재시작해도 worker에 돌아가고 있으면 데이터 안모은다.**


### 대박) slug받는 view_func을 만들고, feed마다 해당 view_func으로 갈 수 있는 property 구현
1. slug를 `path`(목적)로 받아 해당 feed 1개를 조회하는 route(view_func: `feed_single`)를 작성한다.
    ```python
    @main_bp.route('/feed/<slug>')
    def feed_single(slug):
        feed = Feed.query.filter_by(slug=slug).first()
        return f"{feed.to_dict()}"
    ```

2. Feed모델에 @property로 자신의 self.slug를 통해 feed_single view_func으로 접속하는 url을 url_for로 만들어내게 한다.
    - feed.absolute_url를 jinja view에서 호출하면 접속할 수 있는 url이 반환될 것이다.
    ```python
    class Feed(BaseModel):
        #...
        @property
        def absolute_url(self):
            return url_for("main.feed_single", slug=self.slug)
    ```
   

3. **이제 feed_list component에서 각 feed의 a태그에 `{{feed.absolute_url}}`을 넣어준다.**
    ```html
    <!-- app/templates/main/components/feed-list-elements.html -->
    {% for feed in feeds %}
    <a href="{{feed.absolute_url}}" class="text-decoration-none">
        <div class="card border-0 pb-5 pb-md-3">
            <div class="row">
                <div class="col-8">
                    <div class="card-body p-0">
                        <div class="pb-2 text-body infScroll-category">{{feed.source.name}}</div>
    ```
    - `<a href="/feed/%EB%8C%80%EA%B5%AC-%EB%8B%AC%EC%84%9C%EA%B5%AC%ED%95%9C%EC%9D%98%EC%82%AC%ED%9A%8C-%EA%B4%80%EB%82%B4-%EC%B7%A8%EC%95%BD%EA%B3%84%EC%B8%B5-%EC%9C%84%ED%95%9C-%ED%95%9C%EB%B0%A9%EC%A3%BC%EC%B9%98%EC%9D%98-%EB%82%98%EC%84%A0%EB%8B%A4" class="text-decoration-none">`
    - `http://localhost:8000/feed/%EB%8C%80%EA%B5%AC-%EB%8B%AC%EC%84%9C%EA%B5%AC%ED%95%9C%EC%9D%98%EC%82%AC%ED%9A%8C-%EA%B4%80%EB%82%B4-%EC%B7%A8%EC%95%BD%EA%B3%84%EC%B8%B5-%EC%9C%84%ED%95%9C-%ED%95%9C%EB%B0%A9%EC%A3%BC%EC%B9%98%EC%9D%98-%EB%82%98%EC%84%A0%EB%8B%A4`
    ```
    {'id': 69, 'title': '대구 달서구한의사회, 관내 취약계층 위한 ‘한방주치의’ 나선다', 'slug': '대구-달서구한의사회-관내-취약계층-위한-한방주치의-나선다', 'url': 'http://www.mjmedi.com/news/articleView.html?idxno=56703', 'thumbnail_url': None, 'category': None, 'body': '[민족의학신문=박숙현 기자] 대구 달서구한의사회가 관내 저소득층을 위해 한의진료를 지원한다.대구 달서구(구청장 이태훈)는 오는 30일까지 저소득취약계층의 건강한 여름나기 지원을 위해 달서구한의사회(회장 정수경)와 지역 한의원의 재능기부로 ‘우리 동네 한방주치의 사업’을 추진한다고 밝혔다.한방주치의 사업은 저소득 취약계층 의료비 부담을 줄이고 체계적으로 건강관리를 할 수 있도록 지원하는 사업이다. 달서구한의사회 회원들의 재능기부로 한의원 38개가 참여해 대상자의 거주지와 가까운 한의원의 한의사를 주치의로 지정해 서비스를 제공하고 있다', 'published': datetime.datetime(2023, 6, 5, 5, 58, 17), 'published_string': '2023년 06월 05일 14시 58분 17초', 'source_id': 4, 'created_at': datetime.datetime(2023, 6, 6, 15, 59, 59, 651068), 'updated_at': datetime.datetime(2023, 6, 6, 15, 59, 59, 651070)}
    ```
   
4. `main/single.html`을 예시로 만들고, route에서 `options로 source, category_source까지 load`해서 조회하여 같이 내려보내기
    - **cls로 관계를 다 options(joinedload().joinedload())한 뒤, slug로 필터링 해서 가져온다.**
    ```python
    @classmethod
    @transaction
    def get_by_slug(cls, slug):
        _Source = cls.source.mapper.class_

        items = cls.query \
            .options(joinedload(cls.source).joinedload(_Source.source_category)) \
            .filter_by(slug=slug) \
            .first()
        
        return items
    ```
    ```python
    @main_bp.route('/feed/<slug>')
    def feed_single(slug):
        # feed = Feed.query.filter_by(slug=slug).first()
        # return f"{feed.to_dict()}"
        feed = Feed.get_by_slug(slug)
        return render_template('main/single.html', feed=feed)
    ```
5. title과 body를 truncate하지 않고 찍을 예정이다.
    ```html
    <!-- app/templates/main/single.html -->
    <div>{{feed.source.source_category.name}} > {{feed.source.name}} </div>
    <div>{{feed.kst_published.strftime("%b %d %Y , %H:%M") }}</div>
    
    <h1>{{feed.title}}</h1>
    <h2>원본링크: {{feed.url}}</h2>
    {{feed.body}}    
    ```