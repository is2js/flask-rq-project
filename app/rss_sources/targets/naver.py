from app.rss_sources.base_source import TargetSource


class Naver(TargetSource):
    NAME = '네이버'
    URL = 'https://www.naver.com/'

    def _generate_urls(self, target_ids):
        return list(map(lambda target_id: f"https://rss.blog.naver.com/{target_id}.xml", target_ids))
