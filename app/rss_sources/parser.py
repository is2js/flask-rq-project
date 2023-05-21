from datetime import datetime, timedelta
from time import mktime

import feedparser
import pytz
from bs4 import BeautifulSoup

from app.rss_sources.utils import parse_logger


class RssParser(object):

    def __init__(self):
        self._source_url = None
        self._og_image_url = None

    def parse(self, text):

        feed = feedparser.parse(text)

        total_count = len(feed.entries)
        if total_count == 0:
            parse_logger.error(f'feed들이 하나도 존재 하지 않습니다.')
            return False

        source = feed['feed']

        self._source_url = source.get('link', None)
        print(f"출저 url: {self._source_url}")
        print(f"출저 제목: {source.get('title', None)}")
        print(f"출저 부제목: {source.get('subtitle', None)}")
        print(f'총 글 갯수: {total_count}')

        for entry in feed.entries:
            data = dict()

            # 여러 target의 link 버튼용 (유튜브) -> 구독하기
            # data['source_name'] = source.get('title', None)
            # data['source_url'] = source.get('link', None)
            data['source'] = dict(
                target_name=source.get('title', None),
                target_url=source.get('link', None)
            )

            data['url'] = entry.get("link")
            data['category'] = _get_category(entry.get("tags"))
            data['title'] = _get_text_title(entry.get("title"))
            data['thumbnail_url'] = _get_thumbnail(entry)

            data['body'] = _get_text_body(entry)

            # published_parsed + mktime + fromtimestamp + pytz
            utc_published = time_struct_to_utc_datetime(entry.get("published_parsed"))
            data['published'] = utc_published
            # 출력용
            kst_published = utc_to_local(utc_published)
            data['published_string'] = kst_published.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")

            yield data


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
    local_datetime = utc_datetime.astimezone(pytz.timezone(zone))  # utc ware -> kst aware
    return local_datetime  # 외부에서 strftime


def _get_utc_target_date(before_days=1, zone='Asia/Seoul'):
    # 익명 now -> KST now -> KST now -1일 00:00 ~ 23:59 -> utc -1일 00:00 ~ 23:59
    # 1.  unknown now -> kst now
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
