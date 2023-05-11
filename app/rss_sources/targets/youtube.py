# from ..base_source import TargetSource
from app.rss_sources.base_source import TargetSource


class Youtube(TargetSource):
    NAME = '유튜브'
    URL = 'https://www.youtube.com/'

    def _generate_urls(self, target_ids):
        return list(map(lambda target_id: self._build_youtube_url(target_id), target_ids))

    @staticmethod
    def _build_youtube_url(target_id):
        BASE_URL = 'https://www.youtube.com/feeds/videos.xml?'
        if target_id.startswith("UC"):
            return BASE_URL + '&' + 'channel_id' + '=' + target_id
        elif target_id.startswith("PL"):
            return BASE_URL + '&' + 'playlist_id' + '=' + target_id
        else:
            raise ValueError(f'UC 또는 PL로 시작해야합니다. Unvalid target_id: {target_id}')
