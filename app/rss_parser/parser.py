from pprint import pprint

import feedparser
import requests
from bs4 import BeautifulSoup
from opengraph_py3 import OpenGraph

from app.utils.loggers import parse_logger


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
        try:
            response = requests.get(url, headers=self.headers if not headers else headers, params=params)
            # if response.status_code != 200:
            #     raise requests.HTTPError
            response.raise_for_status()  # Raises :class:`HTTPError`, if one occurred.
            return response.text
        except requests.HTTPError:
            parse_logger.error(f'requests 요청 실패(target_id: {self.target_id}, url: {url})')
            return False

    def parse(self):
        # feed = feedparser.parse(self._url)
        # if feed.status != 200:
        #     return False

        result_text = self.requests_url(self._url)
        if not result_text:
            return False

        feed = feedparser.parse(result_text)

        total_count = len(feed.entries)
        if total_count == 0:
            parse_logger.error(f'현재 target_id({self.target_id})에 feed들이 하나도 존재 하지 않습니다.')
            return False

        # Print 블로그 정보가 'feed'에 담겨있음.
        # - https://waylonwalker.com/parsing-rss-python/
        print('------------')
        source = feed['feed']

        print(f"출저 타입: {source['generator']}")
        self._source_url = source['link']
        print(f"출저 url: {self._source_url}")
        print(f"출저 제목: {source['title']}")
        print(f"출저 부제목: {source['subtitle']}")
        print(f'총 글 갯수: {total_count}')

        thumb_count = 0

        # Print 각 글들은 entries에 담겨있음. all title in entries
        # - 1개만 출력
        for entry in feed.entries:
            print('==============')
            print(f'카테고리: {_get_category(entry.get("tags"))}')
            # print(f'제목: {entry.get("title")}')
            print(f'제목: {_get_text_title(entry.get("title"))}')
            thumbnail = _get_thumbnail(entry) or self._get_og_image_url() or \
                self._get_naver_post_image_url(entry.get("link"))

            if thumbnail:
                thumb_count += 1
            print(f'thumbnail : {thumbnail}')
            # print(f'내용: {entry.get("summary")}')
            # print(f'내용: {_get_text_body(entry)}')
            print(f'링크: {entry.get("link")}')
            # 날짜: 2019-02-21 02:18:24
            print(f'날짜: {_struct_to_datetime(entry.get("published_parsed"))}')
            # break
        print("thumb_count", thumb_count)
        return feed

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


def _struct_to_datetime(published_parsed):
    if not published_parsed:
        return None

    from datetime import datetime
    from time import mktime

    # mktime -> seconds로 바꿔줌 +  fromtimestamp -> seconds를 datetime으로 바꿔줌
    return datetime.fromtimestamp(mktime(published_parsed))


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


if __name__ == '__main__':
    # tistory_parser = TistoryParser('nittaku')
    # tistory_parser.parse()

    naver_parser = NaverParser('studd')
    naver_parser.parse()
