from .targets import *
from .urls import *

if __name__ == '__main__':
    from pprint import pprint
    ...
    # print(Tistory('nittaku')._urls)
    # print(Naver('is2js')._urls)
    # print(Youtube('UChZt76JR2Fed1EQ_Ql2W_cw')._urls)

    tistory = Tistory('nittaku')
    pprint(tistory.fetch_feeds())
    # naver = Naver('is2js')
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
