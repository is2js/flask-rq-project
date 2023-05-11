from app.rss_sources.base_source import TargetSource


class Tistory(TargetSource):
    NAME = '티스토리'
    URL = 'https://www.tistory.com/'

    def _generate_urls(self, target_ids):
        return list(map(lambda target_id: f"https://{target_id}.tistory.com/rss", target_ids))
