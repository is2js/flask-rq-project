from app.rss_sources.services import YoutubeService, BlogService, URLService
from app.utils import schedule_logger


def fetch_rss():
    try:
        youtube_service = YoutubeService()
        youtube_updated = youtube_service.fetch_new_feeds()
    except Exception as e:
        schedule_logger.info(f'{str(e)}', exc_info=True)
    try:
        blog_service = BlogService()
        blog_updated = blog_service.fetch_new_feeds()
    except Exception as e:
        schedule_logger.info(f'{str(e)}', exc_info=True)

    try:
        url_service = URLService()
        url_updated = url_service.fetch_new_feeds()
    except Exception as e:
        schedule_logger.info(f'{str(e)}', exc_info=True)
