### 참고
- 참고: 멀티URL + 파싱 https://waylonwalker.com/parsing-rss-python/
- 참고1: Source + Article + Youtbe튜토리얼 : https://github.com/code-tutorials/python-feedreader/blob/master/models/source.py
  - 유튜브: https://www.youtube.com/watch?v=0eEJC4NwoqU&list=PLmxT2pVYo5LBcv5nYKTIn-fblphtD_OJO&index=11
- 참고2: fastapi버전 + bs4 이미지파싱까지: https://github.com/wybiral/firehose/blob/master/parsers/rss/__init__.py

```python
Tistory	https://hyune-c.tistory.com/rss
네이버2: url = 'https://rss.blog.naver.com/{아이디}.xml'
Github  https://{아이디}.github.io/feed.xml


유튜브1:https://www.youtube.com/feeds/videos.xml?channel_id=(채널 ID)
유튜브3: https://www.youtube.com/feeds/videos.xml?playlist_id=(플레이리스트 ID)
유튜브 썸네일1: https://img.youtube.com/vi/%7B%EC%95%84%EC%9D%B4%EB%94%94%7D/maxresdefault.jpg
유튜브 썸네일2: https://img.youtube.com/vi/%7B%EC%95%84%EC%9D%B4%EB%94%94%7D/hqdefault.jpg

Medium	https://medium.com/feed/@{아이디}
Brunch	프로필에서 '페이지 소스 보기' 후 RSS 검색

디스코드봇 활용법: https://discordbot.tistory.com/7
```
#### table을 이용한 카드 마크다운예시
<!-- YOUTUBE:START --><table><tr><td><a href="https://www.youtube.com/watch?v=fj73bxmP03g"><img width="140px" src="https://i.ytimg.com/vi/fj73bxmP03g/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=fj73bxmP03g">നിങ്ങൾ ഒരു വിദ്യാർത്ഥിയാണെങ്കിൽ ഇതിനെക്കുറിച്ച് അറിയു - Microsoft Learn Student Ambassadors Program</a><br/>Feb 11, 2023</td></tr></table>
<table><tr><td><a href="https://www.youtube.com/watch?v=qOckacF3WJo"><img width="140px" src="https://i.ytimg.com/vi/qOckacF3WJo/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=qOckacF3WJo">[Selected] GitHub Campus Experts Application Video | Feb 2022 | Kerala</a><br/>Aug 6, 2022</td></tr></table>
<table><tr><td><a href="https://www.youtube.com/watch?v=EXDn6uWs254"><img width="140px" src="https://i.ytimg.com/vi/EXDn6uWs254/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=EXDn6uWs254">&lpar;+1 Computer Science&rpar; Discipline of Computing #7 - Generations of Computer Pt.3 | Kerala Syllabus</a><br/>Nov 24, 2021</td></tr></table>
<table><tr><td><a href="https://www.youtube.com/watch?v=-HwTYq1BL50"><img width="140px" src="https://i.ytimg.com/vi/-HwTYq1BL50/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=-HwTYq1BL50">&lpar;+1 Computer Science&rpar; Discipline of Computing #6 - Generations of Computer Pt.2 | Kerala Syllabus</a><br/>Nov 14, 2021</td></tr></table>
<table><tr><td><a href="https://www.youtube.com/watch?v=GFsyBBRKOqE"><img width="140px" src="https://i.ytimg.com/vi/GFsyBBRKOqE/mqdefault.jpg"></a></td>
<td><a href="https://www.youtube.com/watch?v=GFsyBBRKOqE">&lpar;+1 Computer Science&rpar; Discipline of Computing #5 - Generations of Computer  Pt.1 | Malayalam</a><br/>Nov 11, 2021</td></tr></table>
<!-- YOUTUBE:END -->



#### youtube parse관련
- youtube source에는 `generator`가 없고, entry에는 카테고리의 `tags`가 없다 -> **`get(, None)`으로 변경해준다.**
- 추가로 thumbnail을 각 entry의 `media_thumbnail`에서 뽑아내는 듯
- blog들과 다르게 entry에는 `15개` 정도만 뿌려주는 듯 하다
    - 그 이상 가져오려면 youtube api를 사용해야 50개까지 내려준다.


### YoutubeParser 구현
- 채널id는 `UC`을 달고, 재생목록은 `PL`를 달고 시작된다 그것을 이용하여 입력 target_id에 대한 url을 만든다.
```python
class YoutubeParser(BaseParser):
    def __init__(self, target_id):
        super().__init__(target_id)
        self._url = _build_youtube_url(target_id)

```
```python
def _build_youtube_url(target_id):
    # 조합: https://github.com/Zaltu/youtube-rss-email/blob/master/BetterYoutube/youtube_utils.py

    BASE_URL = 'https://www.youtube.com/feeds/videos.xml?'

    if target_id.startswith("UC"):
        return BASE_URL + '&' + 'channel_id' + '=' + target_id
    elif target_id.startswith("PL"):
        return BASE_URL + '&' + 'playlist_id' + '=' + target_id
    else:
        raise ValueError(f'UC 또는 PL로 시작해야합니다. Unvalid target_id: {target_id}')
```

### date 필터적용하기

#### datetime을 utc -> local(kst)로 변경하여 strftime으로 출력하기
- 참고: https://spoqa.github.io/2019/02/15/python-timezone.html

1. **youtube 외 blog의 rss들도 모두 `utc`로 뿌려준다.**
    - Model에 저장할거면 `Datetime(timezone=True)`로 두면, `kst도 utc로 자동변환 저장`된다고 한다.
    - **이미 utc형태로 time.struct가 넘어오기 때문에 naive datetime으로 만든 뒤, `pytz.utc.localize( naive_datetime )`을 `먼저 변환`해줘야한다**
    - 이 때, kst로 .localize()하면, `naive_datetime의 시각이 이미 utc기준`이라서 제대로 안된다.
    - **utc로 일단 뽑아놓고, `출력을 위한 kst로 변환`, `비교시 utc기준으로 할 예정`이므로 1단계는 `utc aware datetime으로의 변환 by pytz`이다.**
    ```python
    def time_struct_to_utc_datetime(published_parsed):
        """
        time_struct(utc, string) -> naive datetime -> utc datetime by pytz
        """
        if not published_parsed:
            return None
    
        # mktime -> seconds로 바꿔줌 +  fromtimestamp -> seconds를 datetime으로 바꿔줌
        naive_datetime = datetime.fromtimestamp(mktime(published_parsed))  # utc naive
    
        utc_datetime = pytz.utc.localize(naive_datetime)  # utc aware [필수]
        return utc_datetime
    ```

2. **이제 `출력을 위한 utc_to_local`로 변환을 해줘야한다.**
    - **이미 utc기준 시각으로 제공-> `utc.localize를 한번한 aware는 astimezone( pytz.timezone( 'local'))`으로 변경해야한다.**
    - `'Asia/Seoul'`로 타임존을 잡고, 현재 utc_datetime에 `.astimezone()`으로 `pytz.timezone( )`에 string으로 넣으면 변경된다.
    ```python
    def utc_to_local(utc_datetime, zone='Asia/Seoul'):
        # 한번 localize를 쓰면, 또는 안됨. utc만 하고, astimezone( pytz.timezone('local'))로 바꿔주기)
        local_datetime = utc_datetime.astimezone(pytz.timezone(zone))  # utc ware -> kst aware
        return local_datetime  # 외부에서 strftime
    ```
   

3. utc string -> utc datetime by pytz.utc.localize -> kst datetime by astimezone 을 거쳤으면, strftime으로 출력용으로 사용한다
    ```python
    utc_published = time_struct_to_utc_datetime(entry.get("published_parsed"))
    
    kst_published = utc_to_local(utc_published)
    print(f'날짜: {kst_published.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")}')
    ```
   

#### 더 쉬운 feee -> utc변환은  published + dateutil.parser.parse(utc_datetime) + utc_to_local(kst_datetime)으로 바로 변환가능하다
```python
# 1) published_parsed + mktime + fromtimestamp + pytz
# utc_published = time_struct_to_utc_datetime(entry.get("published_parsed"))

# 2) published + datetutil + pytz
utc_published = parser.parse(entry.get('published'))
```

#### kst기준 특정날짜(전날 0시 ~23시59분) -> utc를 변환하여, UTC로 필터링하기
1. 타겟을 기본으로 `kst 기준 1일 전`으로 잡는다. **2개의 datetime을 dict로 전달한다**
    - **DB에 저장될 datetime은 utc이다. `system(unknown) -> local(kst)기준으로 start, end date를 먼저 만들고` -> `utc로 변환하여 필터링`하도록 미리 짜본다**
    - **이 때, 시작이 utc기준의 string이 아닌 `local의 datetime.now()`이므로 `local_timezone.localize()`로 시작 후 추가변환은 .astimezone()을 이용한다**
    ```python
    def _get_utc_target_date(before_days=1, zone='Asia/Seoul'):
        #### 익명 now -> KST now -> KST now -1일 00:00 ~ 23:59 -> utc -1일 00:00 ~ 23:59
    
        # 1.  unkownn now -> kst now
        local_now = pytz.timezone(zone).localize(datetime.now())
        # 2.  kst now -> kst target_datetime
        kst_target_datetime = local_now - timedelta(days=before_days)
    
        # 3.  kst target_datetime -> kst target_date 0시 + 23시59분(.replace) -> utc target_date 시작시간 + 끝시간  
        # - replace로 timezone을 바꾸지 말 것.
        utc_target_start = kst_target_datetime.replace(hour=0, minute=0, second=0, microsecond=0) \
            .astimezone(pytz.utc)
        utc_target_end = kst_target_datetime.replace(hour=23, minute=59, second=59, microsecond=999999) \
            .astimezone(pytz.utc)
    
        return dict(start=utc_target_start, end=utc_target_end)
    ```

2. 적용하여, 전날 feed가 필터링에 걸리는지 확인한다.
    ```python
    utc_published = time_struct_to_utc_datetime(entry.get("published_parsed"))
    # 출력용
    kst_published = utc_to_local(utc_published)
    print(f'날짜: {kst_published.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")}')
    # 필터링용
    target_date = _get_utc_target_date(before_days=1)
    print("target_date['start']", target_date['start'])
    print("utc_published", utc_published)
    print("target_date['end']", target_date['end'])
    is_target = target_date['start'] <= utc_published <= target_date['end']
    print(f'업데이트 대상 여부: {is_target}')
    ```
    ```
    날짜: 2023년 05월 10일 05시 25분 48초
    target_date['start'] 2023-05-09 15:00:00+00:00
    utc_published 2023-05-09 20:25:48+00:00
    target_date['end'] 2023-05-10 14:59:59.999999+00:00
    업데이트 대상 여부: True
    ```
   

