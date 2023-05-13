from app.rss_sources.base_source import TargetSource


class Tistory(TargetSource):
    NAME = '티스토리'
    URL = 'https://www.tistory.com/'
    TARGET_URL = 'https://{}.tistory.com/rss'

    def map(self, feed):
        if not feed['thumbnail_url']:
            feed['thumbnail_url'] = self._get_og_image_url(feed['url'])

        return feed
