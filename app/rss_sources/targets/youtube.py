# from ..base_source import TargetSource
from app.rss_sources.base_source import TargetSource


class Youtube(TargetSource):
    NAME = '유튜브'
    URL = 'https://www.youtube.com/'
    # TARGET_URL = 'https://{}.tistory.com/rss'

    def _get_target_url_from_id(self, target_id):
        """
        상수로 target_id -> target_url을 만들 수 없으니
        id로부터 _generate_urls내부의 target_id로부터 url을 만들어주는 메서드를 오버라이딩해서 재정의
        """
        BASE_URL = 'https://www.youtube.com/feeds/videos.xml?'
        if target_id.startswith("UC"):
            return BASE_URL + '&' + 'channel_id' + '=' + target_id
        elif target_id.startswith("PL"):
            return BASE_URL + '&' + 'playlist_id' + '=' + target_id
        else:
            raise ValueError(f'UC 또는 PL로 시작해야합니다. Unvalid target_id: {target_id}')

