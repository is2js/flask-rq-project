from bs4 import BeautifulSoup

from app.rss_sources.sources.base_source import TargetSource
from app.rss_sources.utils import requests_url


class Naver(TargetSource):
    NAME = '네이버'
    URL = 'https://www.naver.com/'
    TARGET_URL = 'https://rss.blog.naver.com/{}.xml'

    def map(self, feed):
        if not feed['thumbnail_url']:
            # 글에 image가 없는 경우, image를 못뽑는다. -> og_image도 일반적으로 바로 안뽑힘 -> images폴더에서 가져오기
            feed['thumbnail_url'] = self._get_naver_post_image_url(feed['url']) or None
                # "./rss_sources/images/naver.png"
                # "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='46' height='21'%3E%3Cpath d='M39.322 3.993c1.486 0 2.584.56 3.339 1.519V4.32H46v11.096C46 19.34 43.004 21 39.962 21v-3.083h.114c1.601 0 2.585-.842 2.585-2.5v-1.075c-.755.958-1.853 1.519-3.34 1.519-3.247 0-5.626-2.71-5.626-5.934s2.379-5.934 5.627-5.934zM3.43.426v4.992c.755-.887 1.875-1.425 3.407-1.425 2.997 0 5.467 2.687 5.467 6.168 0 3.48-2.47 6.167-5.467 6.167-1.532 0-2.652-.537-3.407-1.425V16H0V.425h3.43zm22.59 3.567c3.362 0 6.06 2.687 6.06 6.168 0 3.48-2.698 6.167-6.06 6.167-3.362 0-6.061-2.687-6.061-6.167 0-3.481 2.699-6.168 6.06-6.168zM12.62 0c2.783.277 5.307 1.997 5.307 5.625v10.376h-3.43V5.625c0-1.408-.698-2.235-1.877-2.468zM6.152 7.076c-1.707 0-2.945 1.189-2.945 3.085 0 1.895 1.238 3.084 2.945 3.084 1.708 0 2.945-1.189 2.945-3.084 0-1.896-1.237-3.085-2.945-3.085zm19.868.102c-1.609 0-2.846 1.188-2.846 2.983 0 1.794 1.237 2.983 2.846 2.983s2.846-1.189 2.846-2.983c0-1.795-1.237-2.983-2.846-2.983zm13.873-.183c-1.757 0-2.995 1.188-2.995 2.932s1.238 2.932 2.995 2.932c1.757 0 2.995-1.188 2.995-2.932s-1.238-2.932-2.995-2.932z' fill='green' fill-rule='evenodd'/%3E%3C/svg%3E"

        return feed

    @staticmethod
    def _get_naver_post_image_url(post_url, first_image=True):
        result_text = requests_url(post_url)
        if not result_text:
            return None

        parsed_post = BeautifulSoup(result_text, features="html.parser")

        main_frame_element = next(iter(parsed_post.select('iframe#mainFrame')), None)
        if main_frame_element is None:
            # parse_logger.debug(f'해당 Naver blog에서 main_frame_element을 발견하지 못했습니다.')
            return None

        main_frame_url = "http://blog.naver.com" + main_frame_element.get('src')

        # main_frame_html = requests.get(main_frame_url).text
        main_frame_html = requests_url(main_frame_url)
        parsed_main_frame = BeautifulSoup(main_frame_html, features="html.parser")

        post_1_div_element = next(iter(parsed_main_frame.select('div#post_1')), None)
        if post_1_div_element is None:
            # parse_logger.debug(f'해당 Naver blog에서 div#post_1을 발견하지 못했습니다.')
            return None

        post_editor_ver = post_1_div_element.get('data-post-editor-version')
        if post_editor_ver is None:
            # parse_logger.debug(f'해당 Naver blog는서 지원하지 않는 버전의 에디터를 사용 중...')
            return None

        components_html = parsed_main_frame.select('div.se-component')
        if not components_html:
            # parse_logger.debug(f'해당 Naver blog에서 div.se-component를 찾을 수 없습니다.')
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
            # parse_logger.debug(
                # f'해당 Naver blog에서 se-component se-image를 가진 component 속 img태그에 data-lazy-src를 발견하지 못했습니다.')
            return None

        # 하나라도 있으면, 첫번째 것만 반환
        return image_urls[0] if first_image else image_urls
