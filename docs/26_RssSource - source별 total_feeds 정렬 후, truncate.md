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


### test로 feed들을 마크다운으로 작성하기
- **여러 target_id를 가질 경우**
  - youtube는 prefix로 `entry`데이터를 생성시 블로그 url(link) `source_title`을 받아와서 처리하게 했다.
  - blog는 prefix로 `Source cls의 NAME`인 `source_category_name`를 받아와서 달게 했다.
```python
# app/rss_sources/__init__.py

from targets import *
from urls import *

if __name__ == '__main__':
    from pprint import pprint

    # Youtube or URLSource들은 category 미반영
    target_ids = [
        'UChZt76JR2Fed1EQ_Ql2W_cw', # 조재성
        'UC-lgoofOVXSoOdRf5Ui9TWw', # 쌍보네TV
    ]
    YOUTUBE_DISPLAY_NUMBERS = 5
    
    
    
    
    youtube = Youtube(target_ids)
    youtube_feeds = youtube.fetch_feeds()

    youtube_feeds.sort(key=lambda f: f['published'], reverse=True)
    youtube_feeds = youtube_feeds[:YOUTUBE_DISPLAY_NUMBERS]

    youtube_markdown_text = '''\
### 🎞 최근 유튜브    
<!-- YOUTUBE:START -->
'''
    youtube_subscript_text = '''\
<div align="center">
    <a href="https://www.youtube.com/c/{}?sub_confirmation=1"><img src="https://img.shields.io/badge/-구독하기-red?style=flat&logo=youtube&logoColor=white" height=35px/></a>
</div>
'''.format(target_ids[0]) if len(target_ids) == 1 else ''

    youtube_markdown_text += youtube_subscript_text

    youtube_table_start = '''\
<div align="center">
    <table>
'''
    youtube_markdown_text += youtube_table_start

    youtube_feed_template = '''\
        <tr>
            <td align="center" width="140px" style="background:black;" style="padding:0;">
                <a href="{}">
                    <img width="140px" src="{}" style="margin:0;">
                </a>
            </td>
            <td>
                <a href="{}" style="color:red;text-decoration: none;">
                    <h4>{}{}</h4>
                </a>
                <small style="color:grey">{}</small>
            </td>
        <tr>
'''.strip()

    for feed in youtube_feeds:
        feed_text = youtube_feed_template.format(
            feed['url'],
            feed['thumbnail_url'],
            feed['url'],
            f'<span style="color:black">{feed["source_category_name"]}) </span>' if len(target_ids) > 1 else '',
            feed['title'],
            feed['published_string']
        )
        youtube_markdown_text += feed_text

    youtube_markdown_text += '''
    </table>
</div>
<!-- YOUTUBE: END -->


'''

    TISTORY_TARGET_ID = 'nittaku'
    NAVER_TARGET_ID = 'is2js'
    BLOG_DISPLAY_NUMBERS = 5
    
    
    
    
    
    tistory = Tistory([(TISTORY_TARGET_ID)])
    tistory_feeds = tistory.fetch_feeds()

    naver = Naver(NAVER_TARGET_ID)
    naver_feeds = naver.fetch_feeds()


    blog_feeds = tistory_feeds + naver_feeds
    blog_feeds.sort(key=lambda f: f['published'], reverse=True)

    del blog_feeds[BLOG_DISPLAY_NUMBERS:]

    # print('total 10개')
    # pprint(blog_feeds)

    blog_markdown_text = '''\
### 📚 최근 블로그

<!-- BLOG:START -->    
<div align="center">
    <table>
'''


    blog_feed_template = '''
        <tr>
            <td align="center" width="120px" style="padding:0;">
                <a href="{}">
                    <img width="120px" src="{}" style="margin:0;" alt="empty">
                </a>
            </td>
            <td>
                <a href="{}" style="color:black;text-decoration: none;">
                    <h5>{}{}</h5>
                </a>
                <small style="color:grey">{}</small>
            </td>
        <tr>
    '''.strip()

    for feed in blog_feeds:
        feed_text = blog_feed_template.format(
            feed['url'],
            feed['thumbnail_url'],
            feed['url'],
            f'<span style="color:darkgrey">{feed["source_category_name"]} </span>',
            feed['title'],
            feed['published_string']
        )
        blog_markdown_text += feed_text

    blog_markdown_text += '''
    </table>
</div>
<!-- BLOG:END -->


'''



    with open("./README.md", "w", encoding='utf-8') as readme:
        readme.write(youtube_markdown_text)
        readme.write(blog_markdown_text)
```

### 🎞 최근 유튜브

<!-- YOUTUBE:START -->

<div align="center">
    <table>
<tr>
            <td align="center" width="140px" style="background:black;" style="padding:0;">
                <a href="https://www.youtube.com/watch?v=1j3wGl06pUs">
                    <img width="140px" src="https://i2.ytimg.com/vi/1j3wGl06pUs/hqdefault.jpg" style="margin:0;">
                </a>
            </td>
            <td>
                <a href="https://www.youtube.com/watch?v=1j3wGl06pUs" style="color:red;text-decoration: none;">
                    <h4><span style="color:black">쌍보네TV </span>여동생을 위한 쌍둥이 오빠들의 축가 | SG워너비 해바리기</h4>
                </a>
                <small style="color:grey">2023년 05월 10일 05시 25분 48초</small>
            </td>
        <tr><tr>
            <td align="center" width="140px" style="background:black;" style="padding:0;">
                <a href="https://www.youtube.com/watch?v=7NER1ikd8AU">
                    <img width="140px" src="https://i4.ytimg.com/vi/7NER1ikd8AU/hqdefault.jpg" style="margin:0;">
                </a>
            </td>
            <td>
                <a href="https://www.youtube.com/watch?v=7NER1ikd8AU" style="color:red;text-decoration: none;">
                    <h4><span style="color:black">조재성 </span>체스 미션 최종 5단계 구현</h4>
                </a>
                <small style="color:grey">2022년 04월 12일 15시 34분 11초</small>
            </td>
        <tr><tr>
            <td align="center" width="140px" style="background:black;" style="padding:0;">
                <a href="https://www.youtube.com/watch?v=GZBNcOFdA1Y">
                    <img width="140px" src="https://i4.ytimg.com/vi/GZBNcOFdA1Y/hqdefault.jpg" style="margin:0;">
                </a>
            </td>
            <td>
                <a href="https://www.youtube.com/watch?v=GZBNcOFdA1Y" style="color:red;text-decoration: none;">
                    <h4><span style="color:black">조재성 </span>포돌이 체스(css적용버전)</h4>
                </a>
                <small style="color:grey">2022년 04월 09일 14시 59분 13초</small>
            </td>
        <tr><tr>
            <td align="center" width="140px" style="background:black;" style="padding:0;">
                <a href="https://www.youtube.com/watch?v=On2Vr3b5Uko">
                    <img width="140px" src="https://i4.ytimg.com/vi/On2Vr3b5Uko/hqdefault.jpg" style="margin:0;">
                </a>
            </td>
            <td>
                <a href="https://www.youtube.com/watch?v=On2Vr3b5Uko" style="color:red;text-decoration: none;">
                    <h4><span style="color:black">조재성 </span>포돌이 체스 4단계 구현</h4>
                </a>
                <small style="color:grey">2022년 04월 07일 17시 49분 24초</small>
            </td>
        <tr><tr>
            <td align="center" width="140px" style="background:black;" style="padding:0;">
                <a href="https://www.youtube.com/watch?v=QimOG53PNkg">
                    <img width="140px" src="https://i2.ytimg.com/vi/QimOG53PNkg/hqdefault.jpg" style="margin:0;">
                </a>
            </td>
            <td>
                <a href="https://www.youtube.com/watch?v=QimOG53PNkg" style="color:red;text-decoration: none;">
                    <h4><span style="color:black">조재성 </span>한의대생들을 위한 근육침법</h4>
                </a>
                <small style="color:grey">2021년 12월 22일 08시 28분 10초</small>
            </td>
        <tr>
    </table>
</div>

<!-- YOUTUBE: END -->



### 📚 최근 블로그

<!-- BLOG:START -->    

<div align="center">
    <table>
<tr>
            <td align="center" width="120px" style="padding:0;">
                <a href="https://blog.naver.com/is2js/223098522367">
                    <img width="120px" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='46' height='21'%3E%3Cpath d='M39.322 3.993c1.486 0 2.584.56 3.339 1.519V4.32H46v11.096C46 19.34 43.004 21 39.962 21v-3.083h.114c1.601 0 2.585-.842 2.585-2.5v-1.075c-.755.958-1.853 1.519-3.34 1.519-3.247 0-5.626-2.71-5.626-5.934s2.379-5.934 5.627-5.934zM3.43.426v4.992c.755-.887 1.875-1.425 3.407-1.425 2.997 0 5.467 2.687 5.467 6.168 0 3.48-2.47 6.167-5.467 6.167-1.532 0-2.652-.537-3.407-1.425V16H0V.425h3.43zm22.59 3.567c3.362 0 6.06 2.687 6.06 6.168 0 3.48-2.698 6.167-6.06 6.167-3.362 0-6.061-2.687-6.061-6.167 0-3.481 2.699-6.168 6.06-6.168zM12.62 0c2.783.277 5.307 1.997 5.307 5.625v10.376h-3.43V5.625c0-1.408-.698-2.235-1.877-2.468zM6.152 7.076c-1.707 0-2.945 1.189-2.945 3.085 0 1.895 1.238 3.084 2.945 3.084 1.708 0 2.945-1.189 2.945-3.084 0-1.896-1.237-3.085-2.945-3.085zm19.868.102c-1.609 0-2.846 1.188-2.846 2.983 0 1.794 1.237 2.983 2.846 2.983s2.846-1.189 2.846-2.983c0-1.795-1.237-2.983-2.846-2.983zm13.873-.183c-1.757 0-2.995 1.188-2.995 2.932s1.238 2.932 2.995 2.932c1.757 0 2.995-1.188 2.995-2.932s-1.238-2.932-2.995-2.932z' fill='green' fill-rule='evenodd'/%3E%3C/svg%3E" style="margin:0;" alt="empty">
                </a>
            </td>
            <td>
                <a href="https://blog.naver.com/is2js/223098522367" style="color:black;text-decoration: none;">
                    <h5><span style="color:darkgrey">네이버 </span>ddd</h5>
                </a>
                <small style="color:grey">2023년 05월 10일 18시 33분 11초</small>
            </td>
        <tr><tr>
            <td align="center" width="120px" style="padding:0;">
                <a href="https://blog.naver.com/is2js/223096950852">
                    <img width="120px" src="https://postfiles.pstatic.net/MjAyMzA1MDlfNDYg/MDAxNjgzNTc3Nzg4NzUy.AlAGwLmQLs2vVPJlB65VyGMf_qAlz63zO1hqmBRa5oYg.qnpSINFxzXsETQftIzrgzBgF9HjTe9WH_zBLmbh58A4g.PNG.is2js/%EB%B0%94%EC%9A%B8%EC%BC%80%EC%96%B4.png?type=w773" style="margin:0;" alt="empty">
                </a>
            </td>
            <td>
                <a href="https://blog.naver.com/is2js/223096950852" style="color:black;text-decoration: none;">
                    <h5><span style="color:darkgrey">네이버 </span>ㅁㄴㅇㄻㄴㅁㄴㅇㄻㄴ</h5>
                </a>
                <small style="color:grey">2023년 05월 09일 05시 29분 55초</small>
            </td>
        <tr><tr>
            <td align="center" width="120px" style="padding:0;">
                <a href="https://nittaku.tistory.com/514">
                    <img width="120px" src="https://img1.daumcdn.net/thumb/R800x0/?scode=mtistory2&fname=https%3A%2F%2Ft1.daumcdn.net%2Ftistory_admin%2Fstatic%2Fimages%2FopenGraph%2Fopengraph.png" style="margin:0;" alt="empty">
                </a>
            </td>
            <td>
                <a href="https://nittaku.tistory.com/514" style="color:black;text-decoration: none;">
                    <h5><span style="color:darkgrey">티스토리 </span>np.random.shuffle 과 np.random.permutation 정리</h5>
                </a>
                <small style="color:grey">2021년 07월 26일 22시 38분 29초</small>
            </td>
        <tr><tr>
            <td align="center" width="120px" style="padding:0;">
                <a href="https://nittaku.tistory.com/513">
                    <img width="120px" src="https://img1.daumcdn.net/thumb/R800x0/?scode=mtistory2&fname=https%3A%2F%2Ft1.daumcdn.net%2Ftistory_admin%2Fstatic%2Fimages%2FopenGraph%2Fopengraph.png" style="margin:0;" alt="empty">
                </a>
            </td>
            <td>
                <a href="https://nittaku.tistory.com/513" style="color:black;text-decoration: none;">
                    <h5><span style="color:darkgrey">티스토리 </span>[원격용] 윈도우키, 한영키, 알트탭 매핑 오토핫키</h5>
                </a>
                <small style="color:grey">2021년 05월 10일 19시 04분 18초</small>
            </td>
        <tr><tr>
            <td align="center" width="120px" style="padding:0;">
                <a href="https://nittaku.tistory.com/512">
                    <img width="120px" src="https://img1.daumcdn.net/thumb/R800x0/?scode=mtistory2&fname=https%3A%2F%2Ft1.daumcdn.net%2Ftistory_admin%2Fstatic%2Fimages%2FopenGraph%2Fopengraph.png" style="margin:0;" alt="empty">
                </a>
            </td>
            <td>
                <a href="https://nittaku.tistory.com/512" style="color:black;text-decoration: none;">
                    <h5><span style="color:darkgrey">티스토리 </span>윈도우에서 markdown 파일을 우클릭 > 새로 만들기에 넣기</h5>
                </a>
                <small style="color:grey">2021년 04월 24일 09시 12분 10초</small>
            </td>
        <tr>
    </table>
</div>

<!-- BLOG:END -->

