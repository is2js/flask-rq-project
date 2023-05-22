from app import Base, engine
from app.rss_sources.markdown_creator import YoutubeMarkdown, BlogMarkdown, URLMarkdown
from app.rss_sources.services import YoutubeService, BlogService, URLService
from .templates import YOUTUBE_FEED_TEMPLATE, BLOG_FEED_TEMPLATE, URL_FEED_TEMPLATE

from app.rss_sources.config import SourceConfig


def get_current_services():
    current_services = []
    if SourceConfig.youtube_target_ids:
        current_services.append(YoutubeService())
    if SourceConfig.tistory_target_id_and_categories or SourceConfig.naver_target_id_and_categories:
        current_services.append(BlogService())
    if SourceConfig.url_and_names:
        current_services.append(URLService())
    return current_services


if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)

    youtube_service = YoutubeService()
    is_updated = youtube_service.fetch_new_feeds()
    print('youtube_feeds 업데이트 여부 >>> ', is_updated)
    blog_service = BlogService()
    is_updated = blog_service.fetch_new_feeds()
    print('blog_feeds 업데이트 여부 >>> ', is_updated)
    url_service = URLService()
    is_updated = url_service.fetch_new_feeds()
    print('url_feeds 업데이트 여부 >>> ', is_updated)

    youtube_feeds = youtube_service.get_feeds()
    blog_feeds = blog_service.get_feeds()
    url_feeds = url_service.get_feeds()
    print('youtube_feeds >>> ', [f.title for f in youtube_feeds])
    print('blog_feeds >>> ', [f.title for f in blog_feeds])
    print('url_feeds >>> ', [f.title for f in url_feeds])

    # append_markdown = ''
    # append_markdown += get_youtube_markdown()
    # append_markdown += get_blog_markdown()
    # append_markdown += get_url_markdown()
    #
    # if append_markdown:
    #     with open('./readme.md', 'w', encoding="UTF-8") as readme:
    #         with open('./default.md', 'r', encoding="UTF-8") as default:
    #             readme.write(default.read()+'\n')
    #         readme.write(append_markdown)
    #
    # else:
    #     parse_logger.info('default readme에 추가할 내용이 없습니다.')

    # os.close()

    # blog의 경우 category 반영 by tuple

    # naver = Naver(('studd',None))
    # pprint(naver.fetch_feeds())
    # [
    #  {
    #   'body': '222asdfsdfasdf333asdfaasdfasdfasdfasa',
    #   'category': '마왕',
    #   'published': datetime.datetime(2023, 5, 10, 18, 33, 11, tzinfo=tzoffset(None, 32400)),
    #   'published_string': '2023년 05월 10일 18시 33분 11초',
    #   'source_category_name': '네이버',
    #   'source_category_url': 'https://www.naver.com/',
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
    #   'source_category_name': '민족의학신문',
    #   'source_category_url': 'https://www.mjmedi.com//',
    #   'thumbnail_url': None,
    #   'title': '심평원 서울지원, 걷기 활동 나눔행사 실시',
    #   'url': 'http://www.mjmedi.com/news/articleView.html?idxno=56571'},
    # pprint(Tistory('nittaku').fetch_feeds())
