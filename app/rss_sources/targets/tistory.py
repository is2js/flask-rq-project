from app.rss_sources.base_source import TargetSource


class Tistory(TargetSource):
    NAME = '티스토리'
    URL = 'https://www.tistory.com/'
    TARGET_URL = 'https://{}.tistory.com/rss'
