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
            f'<span style="color:black">{feed["source_title"]}) </span>' if len(target_ids) > 1 else '',
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
            f'<span style="color:darkgrey">{feed["source_name"]} </span>',
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

    # blog의 경우 category 반영 by tuple


    # naver = Naver(('studd',None))
    # pprint(naver.fetch_feeds())
    # [
    #  {
    #   'body': '222asdfsdfasdf333asdfaasdfasdfasdfasa',
    #   'category': '마왕',
    #   'published': datetime.datetime(2023, 5, 10, 18, 33, 11, tzinfo=tzoffset(None, 32400)),
    #   'published_string': '2023년 05월 10일 18시 33분 11초',
    #   'source_name': '네이버',
    #   'source_url': 'https://www.naver.com/',
    #   'thumbnail_url': None,
    #   'title': 'ddd',
    #   'url': 'https://blog.naver.com/is2js/223098522367'
    #   },
    # ]


    # pprint(민족의학신문('http://www.mjmedi.com/rss/clickTop.xml').fetch_feeds())
    # [{'body': '[민족의학신문=김춘호 기자] 건강보험심사평가원 서울지원(지원장 지점분, 이하 서울지원)은 10일 서울 동작구 소재 '
    #           '굿네이버스 서인지역본부(본부장 홍선교)를 방문해 어린이 놀이키트를 전달했다고 밝혔다.이번 나눔행사는 심사평가원이 실시한 '
    #           '임직원 ESG 실천 프로젝트 ‘HIRA人 한마음 워킹챌린지 부서대항전’에서 서울지원을 포함한 부산지원과 의료급여실이 각 '
    #           '조별 우승팀으로 선정되어 지역사회에 물품을 후원할 기회가 주어졌다. 이에 서울지원은 아동양육시설 어린이들을 위한 놀이키트 '
    #           '6세트를 후원했고, 해당 키트는 보육원 6곳에 각각 비치 될',
    #   'category': None,
    #   'published': datetime.datetime(2023, 5, 10, 16, 29, 45),
    #   'published_string': '2023년 05월 10일 16시 29분 45초',
    #   'source_name': '민족의학신문',
    #   'source_url': 'https://www.mjmedi.com//',
    #   'thumbnail_url': None,
    #   'title': '심평원 서울지원, 걷기 활동 나눔행사 실시',
    #   'url': 'http://www.mjmedi.com/news/articleView.html?idxno=56571'},
    # pprint(Tistory('nittaku').fetch_feeds())


