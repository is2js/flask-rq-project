### model을 고려하여, targets -> blogs + youtube로 패키지 나누기
1. targets 패키지를 `blogs`로 변경하고
2. youtube 패키지를 만들어, youtube.py를 만들고 init에 import한다
3. markdown_creator.py에서는 `from targets import *`를 blos, youtube 에서 import하도록 바꾼다.
    ```python
    # app/rss_sources/markdown_creator.py
    from blogs import *
    from youtube import *
    from urls import *
    
    
    class Markdown:
        #...
    ```
   

### models.py 붙이기
- Source별(Blog, Youtube, URL) feed들을 보관해야한다?!
  - fetch_feeds시, 각 source정보가 없으면 create, 있으면 get한다?!
  - source모델이 존재해야, 각 source별 데이터를 쉽게 얻고 조회한다?
  - **아니라면, 직접 매번 feed모델의 source_category_name을 검색조건에 포함해야한다.**

#### 분석

1. 일단 Source로 분리하기 전에 Feed정보를 모아본다
    - parser.parse() 내부
        -  source_title: 개별source name(youtube prefix)
        -  source_link : rss http url -> X
        -  url
        -  category
        -  title
        -  thumbnail_url
        -  body
        -  published
        -  published_string
   - fetch_feeds() 내부
        - source_name: 사용자입력 NAME(blog prefix)
        - source_url: 사용자입력 http URL(url link)

2. 사실상 source_name은 source의 category느낌이고, source_title이 source_name느낌이다.
    - `SourceCategory` -> source_name, source_url from `Source cls의 NAME, URL 사용자입력`
    - `Source` -> source_category_id(fk), source_title, source_link 
    - `SourceFeed` -> source_id(fk), 나머지필드


#### 분석에 따른 필드명 변경
1. 아래와 같이 model별 필요한 필드를 구분한다
    - source_name -> source_category_name
    - source_url -> source_category_url
    - source_link -> source_url
    - source_title -> source_name