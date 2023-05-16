1. 내 프로필repo를 clone
2. readme.md를 복사해서 `default.md`만들기
3. `python -m venv venv`로 가상환경 만들고, `.gitignore`에 걸기
    - 프로젝트 설정에서 해당 venv를 인터프리터로 적용하기
4. rss_sources 패키지를 복사해서 붙이기
    - 경로 수정하기(app. 을 제거)
    - 필요한 패키지들 설치(bs4, opengraph_py3, python-dotenv, pytz, feedparser, requests)
5. utils.py에 logger cls 세팅
   - config.py에 세팅
   ```python
    # log폴더 설정
    BASE_FOLDER = Path(__file__).resolve().parent  # BASE_FOLDER:  /계정명/rss_sources
    LOG_FOLDER = BASE_FOLDER.parent.joinpath('logs')  # LOG_FOLDER:  /계정명 + logs
    ```
    - gitigrnore에 `logs`폴더 추가
6. root에 manage.py 생성 후 작동코드 작성
    ```python
    from rss_sources import get_youtube_markdown, get_blog_markdown, get_url_markdown, parse_logger
    
    append_markdown = ''
    append_markdown += get_youtube_markdown()
    append_markdown += get_blog_markdown()
    append_markdown += get_url_markdown()
    
    if append_markdown:
        with open('./readme.md', 'w', encoding="UTF-8") as readme:
            with open('./default.md', 'r', encoding="UTF-8") as default:
                readme.write(default.read() + '\n')
            readme.write(append_markdown)
    
    else:
        parse_logger.info('default readme에 추가할 내용이 없습니다.')
    ```
   
7. 실행후 모든 경로에 `rss_sources.` 추가

### template 수정
1. github의 markdown render는 a태그 안의 h5태그 등을 작동못시킨다
   - 또한 small태그도 table안에 작동안된다.
   - small태그 대신 sup+sub태그를 입히고
   - h5태그는 a태그 밖으로 빼는 등의 수정한다.

2. data: svg파일을 못읽는다. 
    - images폴더를 만들고, default이미지를 만들어놓고
    - 각 Blog Source의 map함수에 넣어준다.
3. **opengraph 패키지를 삭제하고 default이미지를 쓰게 한다**

4. requirements.txt freeze


### github action
- 기본 튜토리얼: https://www.daleseo.com/github-actions-first-workflow/
- cache: https://myjorney.tistory.com/m/entry/Github-Workflow%EC%97%90%EC%84%9C-Python-%ED%8C%A8%ED%82%A4%EC%A7%80-%EC%84%A4%EC%B9%98-%EC%8B%9C%EA%B0%84-%EB%8B%A8%EC%B6%95%ED%95%98%EA%B8%B0?utm_source=facebook&utm_medium=ask-django&utm_campaign=posting&fbclid=IwAR1Uo0mL3s-6PWo8uaTBF6MGZtFE3jhGfitYS8mlFe0donamDid5ryL43HM

1. github에 actions탭에서 set action workflow 생성
2. main.yml에 아래와 같이 정의
    - **cache를 사용하려면 `actions/setup-python@v4`를 써야한다**
    ```python
    name: Python application
    
    on:
      push:
        branches: [ "main" ]
      pull_request:
        branches: [ "main" ]
      schedule:
    #       - cron: "0 0 */1 * *" # 매일 00시00분에
    #      - cron: "*/5 * * * *" # 5분마다 for test
          - cron: "0 */6 * * *" # 6시간마다
    
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - name: Checkout
            uses: actions/checkout@v3
          - name: Set up Python
            uses: actions/setup-python@v4
            # here
            with: 
              python-version: 3.10.7
              cache: pip
              cache-dependency-path: ./requirements.txt
          - name: Install dependencies
            run: |
              python -m pip install --upgrade pip
              pip install -r ./requirements.txt
          - name: Run manage.py
            run: |
              python manage.py
          - name: View Today logs
            run: |
              cat logs/parse.log
          - name: Update README.md file
            run: | 
              git pull
              git add .
              git diff
              git config --local user.email "tingstyle1@gmail.com"
              git config --local user.name "is2js"
              git commit -m "update readme.md"
              git push
    ```