from app import sse
from app.rss_sources import YoutubeService, BlogService, URLService
from app.tasks.decorators import scheduled_task
from app.utils import schedule_logger
from app.rss_sources.config import SourceConfig


@scheduled_task
def fetch_rss():
    try:
        if SourceConfig.youtube_target_ids:
            youtube_service = YoutubeService()
            new_feeds = youtube_service.fetch_new_feeds()
            if new_feeds:
                sse.publish(f'feed__youtubeAdded', channel='youtube')
    except Exception as e:
        schedule_logger.info(f'{str(e)}', exc_info=True)

    try:
        if SourceConfig.tistory_target_id_and_categories or SourceConfig.naver_target_id_and_categories:
            blog_service = BlogService()
            new_feeds = blog_service.fetch_new_feeds()
            if new_feeds:
                sse.publish(f'feed__blogAdded', channel='blog')
    except Exception as e:
        schedule_logger.info(f'{str(e)}', exc_info=True)

    try:
        if SourceConfig.url_and_names:
            url_service = URLService()
            new_feeds = url_service.fetch_new_feeds()
            if new_feeds:
                sse.publish(f'feed__urlAdded', channel='url')

    except Exception as e:
        schedule_logger.info(f'{str(e)}', exc_info=True)
