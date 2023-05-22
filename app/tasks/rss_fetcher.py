from app.rss_sources import get_current_services
from app.utils import schedule_logger


def fetch_rss():

    service_list = get_current_services()

    for service in service_list:
        try:
            new_feeds = service.fetch_new_feeds()
        except Exception as e:
            schedule_logger.info(f'{str(e)}', exc_info=True)


