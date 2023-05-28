### 초기 파일
- https://github1s.com/SamEdwardes/htmx-python-course/blob/main/code/ch6_active_search/ch6_final_video_collector/templates/videos/category.html#L43-L54

1. templates
    - search.html -> feeds.html
    - partials/search_result.html -> 일단 화면에서 다 뿌리기
    - shared/partials/_video_image.html -> 일단 화면에서 다 뿌리기

### feeds.html 필터링없이 모든 feed 반환하기
1. 전체 feed에 대한 route를 작성한다
    ```python
    @rss_bp.route('/categories/all')
    def get_all_feeds():
        service_list = get_current_services()
        feeds = []
        for service in service_list:
            feeds += service.get_feeds()
        return render_template('/rss/feeds.html', feeds=feeds)
    ```
2. `partials/search_result.html`에서 개별 item뿌리는 것을 `feeds.html`로 옮겨놓는다.
    - img태그가 가운데 정렬되도록 `text-center`를 준다
    - img태그 자체는 **높이 고정해놓고 자유롭게 처리되도록 `img-fluid`를 준다**
    - text들이 수직가운데정렬되도록 `my-auto`를 준다
    - title크기를 h5 + bold로 준다
    ```html
    {% extends "shared/_layout.html" %}
    {% block main_content %}
    
        <div class="search-inputs">
            <h1>Search video collector</h1>
            <input
                    name="search_text"
                    placeholder="Search for a video ..."
                    class="form-control"
                    type="text"
                    value="{{ search_text or '' }}"
                    hx-get="/videos/search"
                    hx-trigger="keyup changed delay:250ms"
                    hx-target="#search-results"
                    hx-push-url="true">
    
        </div>
    
        <div class="videos search-results" id="search-results">
            <div class="search-result-count">{{ feeds | length }} results</div>
            <div class="container">
                {% for feed in feeds %}
                    {% if feed %}
                    <div class="row search-result-row">
                        <div class="col-md-2"></div>
                        <div class="video search-result col-md-3 text-center">
                            <a href="{{ feed.url }}">
                                <img src="{{feed.thumbnail_url or url_for('static', filename='/image/source_categories/' + feed.source.source_category.name + '.png') }}"
                                     class="img img-responsive {{ ' '.join(classes) }} img-fluid"
                                     alt="{{ feed.title }}"
                                     title="{{ feed.title }}"
                                     height="100px"
                                >
                            </a>
                        </div>
                        <div class="video search-result col-md-6 my-auto">
                                <div><a href="{{ feed.url }}" class="h5 font-weight-bold">{{ feed.title }}</a></div>
                                <div><span class="author">{{ feed.source.target_name }}</span></div>
                                <div>{{ feed.published_string }} views</div>
                        </div>
                        <div class="col-md-1"></div>
                    </div>
                    {% endif%}
                {% endfor %}
            </div>
    
        </div>
    
    {% endblock %}
    
    {% block title %}Search @ Video Collector{% endblock %}
    ```
    ![img.png](images/all_feeds.png)


### categories -> 클릭시 특정카테고리의 feed들 다 나타나도록
