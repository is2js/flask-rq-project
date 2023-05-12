from app.rss_sources.base_source import TargetSource


class Naver(TargetSource):
    NAME = '네이버'
    URL = 'https://www.naver.com/'
    TARGET_URL = 'https://rss.blog.naver.com/{}.xml'

    # def _generate_urls(self, target_id_and_categories):
    #     return list(map(lambda x: (f"https://rss.blog.naver.com/{x[0]}.xml", x[1]), target_id_and_categories))
