from datetime import datetime, timedelta
from time import mktime

import feedparser
import pytz
import requests
from bs4 import BeautifulSoup
from opengraph_py3 import OpenGraph

from app.utils.loggers import parse_logger

from dateutil import parser


class BaseParser(object):
    def __init__(self, target_id):
        self.target_id = target_id
        self._url = None  # 공통 parse함수를 위해, 미리 초기화
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
        }
        # og:image 를 가져오기 위한, 첫번째 parse때 저장되는 blog의 url
        # - entry의 link로 og:image구하면, 티스토리 이미지가 나옴 ->  블로그의 og:image는 지정한 이미지가 나옴
        # - og:image는 thumbnail없는 경우 공통이므로, 1번 구해놓고 상태값으로 줘 -> 재활용
        self._source_url = None
        self._og_image_url = None

    def requests_url(self, url, headers=None, params=None):
        response = requests.get(url, headers=self.headers if not headers else headers, params=params, timeout=3)
        try:
            # if response.status_code != 200:
            #     raise requests.HTTPError
            response.raise_for_status()  # Raises :class:`HTTPError`, if one occurred.
            return response.text
        except requests.exceptions.ReadTimeout:
            parse_logger.error(f'[ReadTimeout] requests 요청 실패(target_id: {self.target_id}, url: {url})')
            return False
        except requests.HTTPError:
            parse_logger.error(f'[HTTPError] requests 요청 실패(target_id: {self.target_id}, url: {url})')
            return False

    def parse(self):

        result_text = self.requests_url(self._url)
        if not result_text:
            return False

        # feed = feedparser.parse(self._url)
        # if feed.status != 200:
        #     return False
        feed = feedparser.parse(result_text)

        total_count = len(feed.entries)
        if total_count == 0:
            parse_logger.error(f'{self.__class__.__name__}의 target_id({self.target_id})에 feed들이 하나도 존재 하지 않습니다.')
            return False

        source = feed['feed']

        # print(f"출저 타입: {source.get('generator', None)}")  # 유튜브엔 없다
        # yield로 1개씩 방출하면서, 그 부모의 name을 data에 추가 삽입 예정

        self._source_url = source.get('link', None)
        print(f"출저 url: {self._source_url}")
        print(f"출저 제목: {source.get('title', None)}")
        print(f"출저 부제목: {source.get('subtitle', None)}")
        print(f'총 글 갯수: {total_count}')

        thumb_count = 0

        for entry in feed.entries:
            # print('==============')
            # 1개씩 for문내부에서 만든 dict를 yield하여 부모에게 방출
            data = dict()
            # url이 uniquekey라서 id로 삽입할 예정인데, id가 있다면 id로 넣고 없으면 url로 넣자
            # if 'id' in entry:
            #     data['id'] = entry['id']
            # else:
            #     data['id'] = entry.get('link')

            # print(f'링크: {entry.get("link")}')
            data['url'] = entry.get("link")

            # print(f'카테고리: {_get_category(entry.get("tags"))}')
            data['category'] = _get_category(entry.get("tags"))

            # print(f'제목: {_get_text_title(entry.get("title"))}')
            data['title'] = _get_text_title(entry.get("title"))

            # if thumbnail:
            #     thumb_count += 1
            # print(f'thumbnail : {thumbnail}')
            thumbnail = _get_thumbnail(entry) or self._get_og_image_url() or \
                        self._get_naver_post_image_url(entry.get("link"))
            data['thumbnail_url'] = thumbnail

            # print(f'내용: {_get_text_body(entry)}')
            data['body'] = _get_text_body(entry)

            # 날짜: 2019-02-21 02:18:24
            # 1) published_parsed + mktime + fromtimestamp + pytz
            # utc_published = time_struct_to_utc_datetime(entry.get("published_parsed"))

            # 2) published + datetutil + pytz
            utc_published = parser.parse(entry.get('published'))
            # print("published + dateutil.parser", utc_published, type(utc_published))
            data['published'] = utc_published

            # 출력용
            kst_published = utc_to_local(utc_published)
            # print(f'날짜: {kst_published.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")}')
            data['published_string'] = kst_published.strftime("%Y년 %m월 %d일 %H시 %M분 %S초") # .strftime("%Y년 %m월 %d일 %H시 %M분 %S초")

            # 필터링용
            # target_date = _get_utc_target_date(before_days=1)
            # print("target_date['start']", target_date['start'])
            # print("utc_published", utc_published)
            # print("target_date['end']", target_date['end'])
            # is_target = target_date['start'] <= utc_published <= target_date['end']
            # print(f'업데이트 대상 여부: {is_target}')
            # break

            yield data

        # print("thumb_count", thumb_count)
        # return feed

    def _get_og_image_url(self):
        if self._og_image_url:
            return self._og_image_url

        og = OpenGraph(self._source_url, features='html.parser')
        # print(og, type(og))
        if not og.is_valid():
            return None

        self._og_image_url = og.get('image', None)
        return self._og_image_url

    def _get_naver_post_image_url(self, post_url, first_image=True):
        result_text = self.requests_url(post_url)
        if not result_text:
            return None

        parsed_post = BeautifulSoup(result_text, features="html.parser")

        main_frame_element = next(iter(parsed_post.select('iframe#mainFrame')), None)
        if main_frame_element is None:
            parse_logger.debug(f'해당 Naver#{self.target_id}에 main_frame_element을 발견하지 못했습니다.')
            return None

        main_frame_url = "http://blog.naver.com" + main_frame_element.get('src')

        main_frame_html = requests.get(main_frame_url).text
        parsed_main_frame = BeautifulSoup(main_frame_html, features="html.parser")

        post_1_div_element = next(iter(parsed_main_frame.select('div#post_1')), None)
        if post_1_div_element is None:
            parse_logger.debug(f'해당 Naver#{self.target_id}에 div#post_1을 발견하지 못했습니다.')
            return None

        post_editor_ver = post_1_div_element.get('data-post-editor-version')
        if post_editor_ver is None:
            parse_logger.debug(f'해당 Naver#{self.target_id}는 지원하지 않는 버전의 에디터를 사용 중...')
            return None

        components_html = parsed_main_frame.select('div.se-component')
        if not components_html:
            parse_logger.debug(f'해당 Naver#{self.target_id}에 div.se-component를 찾을 수 없습니다.')
            return None

        image_urls = []
        for i, component_html in enumerate(components_html):
            if i == 0:
                # 처음에는 무조건 헤더부분의 다큐먼트 타이틀이 나와 pass한다
                continue

            component_string = str(component_html)
            # 이미지 컴포넌트가 아니면 탈락
            if "se-component se-image" not in component_string:
                continue

            for img_tag in component_html.select('img'):
                img_src = img_tag.get('data-lazy-src', None)
                if img_src is None:
                    continue
                image_urls.append(img_src)

        # 하나도 없으면 탈락
        if len(image_urls) == 0:
            parse_logger.debug(
                f'해당 Naver#{self.target_id}에 se-component se-image를 가진 component 속 img태그에 data-lazy-src를 발견하지 못했습니다.')
            return None

        # 하나라도 있으면, 첫번째 것만 반환
        return image_urls[0] if first_image else image_urls


def _get_category(tags):
    if tags:
        return tags[0].get("term", None)
    return None


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


def utc_to_local(utc_datetime, zone='Asia/Seoul'):
    # 한번 localize를 쓰면, 또는 안됨. utc만 하고, astimezone( pytz.timezone('local'))로 바꿔주기)
    local_datetime = utc_datetime.astimezone(pytz.timezone(zone))  # utc ware -> kst aware

    # 그래서 pytz를 사용할 때는 pytz.timezone.localize()를 항상 써야 하고, .astimezone()같은 파이썬의 표준 메서드들을 사용하고 싶다면 datetime.timezone을 사용해야 합니다.
    # SQLAlchemy DB 모델 객체의 DateTime 컬럼에서 timezone=True 옵션을 켜서 사용하고 있습니다.
    # => DateTime 칼럼에 timezone=True 옵션을 사용하면, SQLAlchemy에서 내부적으로 datetime 객체를 UTC로 저장합니다. 따라서, 별도로 datetime 객체를 UTC로 변환해주지 않아도 자동으로 UTC로 저장됩니다.
    #   class MyModel(Base):
    #     __tablename__ = 'my_table'
    #     id = Column(Integer, primary_key=True)
    #     my_datetime = Column(DateTime(timezone=True))

    #   my_object = MyModel(my_datetime=kst_time)

    return local_datetime  # 외부에서 strftime


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


def _get_shortest_html_body(entry):
    """
    1. 어떤 곳에선 summary 대신 content에 내용이 들어가는 경우도 있으니 2개를 각각 추출해 list로 만든다.
    2. len로 정렬후 짧은 것 1개만 가져간다
    """
    html_body_list = []
    # entry['summary']를 추출
    if 'summary' in entry:
        html_body_list.append(entry.get('summary'))

    # entry['content']에서 'type' == 'text/html' 일 때, 'value'를 추출
    if 'content' in entry:
        for content in entry.get('content'):
            if content['type'] != 'text/html':
                continue
            html_body_list.append(content['value'])

    # 2곳에서 다 추출했는데, 한개도 없다면 return None
    if len(html_body_list) == 0:
        return None

    # html_body_list의 각 html_body들을 len순으로 정렬한 뒤, 제일 짧은 것을 반환한다
    html_body_list.sort(key=lambda x: len(x))
    return html_body_list[0]


def _get_text_body(entry):
    html_body = _get_shortest_html_body(entry)
    # <p>1. shuffle은 inplace=True로 섞어준다.</p>
    parsed_body = BeautifulSoup(html_body, 'html.parser')
    # <p>1. shuffle은 inplace=True로 섞어준다.</p>

    # 1. shuffle은 inplace=True로 섞어준다.
    return parsed_body.get_text().strip()


def _get_text_title(html_title):
    return BeautifulSoup(html_title, 'html.parser').get_text().strip()


def _get_thumbnail(entry):
    # 1. 'media_thumbnail'에서 찾아서, 첫번째 것[0]의 url을 챙긴다.
    if 'media_thumbnail' in entry and len(entry['media_thumbnail']) > 0:
        # print('media_thumbnail 에서 발견')
        return entry['media_thumbnail'][0]['url']

    # 2. 'media_content'에서 찾아서, 첫번째 것[0]에서 url이 있을시 챙긴다
    if 'media_content' in entry and len(entry['media_content']) > 0:
        if 'url' in entry['media_content'][0]:
            # print('media_content 에서 발견')
            return entry['media_content'][0]['url']

    # 3. 'links'에서 찾아서, 각 link 들 중 'type'에 'image'를 포함하는 것들만 모은 뒤, 존재할 경우 첫번째 것[0]의 'href'를 챙긴다
    if 'links' in entry and len(entry['links']) > 0:
        images = [x for x in entry['links'] if 'image' in x['type']]
        if len(images) > 0:
            # print('links 에서 발견')
            return images[0]['href']

    # 4. 지금까지 없었는데, summary(body)가 없다면 아예 없는 것이다.
    #    - summary부터는 bs4로 파싱한 뒤, img태그를 찾는다.
    if 'summary' not in entry:
        return None

    # No media attachment or thumbnail? look for <img> in body...
    # 4-1. find_all이 아닌 find로 img태그를 찾아보고 없으면 None이다.
    parsed_body = BeautifulSoup(entry['summary'], 'html.parser')

    img_tags = parsed_body.find_all('img')
    if img_tags is None:
        return None

    for img_tag in img_tags:
        # 4-2. img태그가 있더라도, 1by1 크기를 가진 것은 없느 것이다.
        if img_tag.get('width', None) == '1':
            continue
        # 4-3. img태그의 'src'가 'yIl2AUoC8zA'를 포함하고 있으면 잘못된 이미지다
        if 'yIl2AUoC8zA' in img_tag['src']:
            continue
        # 4-4. my) 발견한 img['src']가 http로 시작하지 않으면, 잘못된 이미지다.
        # ex> thumbnail_url: data:image/png;base64,iVBORw...
        if not img_tag['src'].startswith('http'):
            continue

        return img_tag['src']
    else:
        return None


class TistoryParser(BaseParser):
    def __init__(self, target_id):
        super().__init__(target_id)
        self._url = f"https://{self.target_id}.tistory.com/rss"


class NaverParser(BaseParser):
    def __init__(self, target_id):
        super().__init__(target_id)
        self._url = f"https://rss.blog.naver.com/{self.target_id}.xml"


# youtube_settings = dict(
#     # channel_id= "UChZt76JR2Fed1EQ_Ql2W_cw",
#     playlist_id="PLjOVTdDf5WwKcFSteiDyPA09toLYZcD1p",
# )


def _build_youtube_url(target_id):
    # 조합: https://github.com/Zaltu/youtube-rss-email/blob/master/BetterYoutube/youtube_utils.py

    BASE_URL = 'https://www.youtube.com/feeds/videos.xml?'

    if target_id.startswith("UC"):
        return BASE_URL + '&' + 'channel_id' + '=' + target_id
    elif target_id.startswith("PL"):
        return BASE_URL + '&' + 'playlist_id' + '=' + target_id
    else:
        raise ValueError(f'UC 또는 PL로 시작해야합니다. Unvalid target_id: {target_id}')


class YoutubeParser(BaseParser):
    def __init__(self, target_id):
        super().__init__(target_id)
        self._url = _build_youtube_url(target_id)


if __name__ == '__main__':
    # tistory_parser = TistoryParser('nittaku')
    # tistory_parser.parse()
    # for feed in tistory_parser.parse():
    #     print(feed)

    naver_parser = NaverParser('is2js')
    # naver_parser.parse()
    for feed in naver_parser.parse():
        print(feed)

    # youtube_parser = YoutubeParser('UC-lgoofOVXSoOdRf5Ui9TWw') # 쌍보네TV
    # youtube_parser.parse()

    # youtube_parser = YoutubeParser('UChZt76JR2Fed1EQ_Ql2W_cw') # 재성
    # for feed in youtube_parser.parse():
    #     print(feed)
