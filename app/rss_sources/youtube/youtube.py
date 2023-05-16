from app.rss_sources.base_source import TargetSource
# from app.rss_sources.templates import TITLE_TEMPLATE, YOUTUBE_CUSTOM_TEMPLATE, TABLE_START, \
#     YOUTUBE_FEED_TEMPLATE, TABLE_END


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


    # def set_custom(self):
    #     custom_result = ''
    #     # 채널명(UC~)을 1개만 입력한 경우 구독하기 버튼
    #     if len(self.target_id_with_categories) == 1 and self.target_id_with_categories[0][0].startswith('UC'):
    #         custom_button = YOUTUBE_CUSTOM_TEMPLATE.format(self.target_id_with_categories[0][0])
    #         custom_result += custom_button
    #
    #     return custom_result
    #
    # def set_feed_template(self, feed_template, feeds):
    #     feed_template_result = ''
    #     for feed in feeds:
    #         feed_text = feed_template.format(
    #             feed['url'],
    #             feed['thumbnail_url'],
    #             feed['url'],
    #             f'<span style="color:black">{feed["source_category_name"]}) </span>' if len(
    #                 self.target_id_with_categories) > 1 else '',
    #             feed['title'],
    #             feed['published_string']
    #         )
    #         feed_template_result += feed_text
    #
    #     return feed_template_result


