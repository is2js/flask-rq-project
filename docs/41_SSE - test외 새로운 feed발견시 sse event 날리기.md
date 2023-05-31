1. `rss_fetcher.py`의 fetch_rss() 메서드는 전체 패치에 대한 new_feed를 받아냇찌만, **우리는 source_category별 sse채널에 publish해야한다.**
    - 그래서 service_list를 순회하며 호출할 때, 그에 맞게 처리되어야한다. 
    - 그럴겨면 SERVICE를 LIST로 묶을 필요가 없다?! (get_feeds시는 사용되느 그대로 두기)
    - 기존의 get_current_services를 없애고 개별로 가져와서 호출하고, sse.publish도 개별로 한다.
    ```python
    # app/tasks/rss_fetcher.py
    from app import sse
    from app.rss_sources import YoutubeService, BlogService, URLService
    from app.utils import schedule_logger
    from app.rss_sources.config import SourceConfig
    
    
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
                    sse.publish(f'feed__urlAdded', channel='blog')
    
        except Exception as e:
            schedule_logger.info(f'{str(e)}', exc_info=True)
    
    ```
2. **db를 다 지운 뒤, 각 카테고리별 빈 페이지를 띄워놓고 -> 스케쥴러를 실행하여, 자동으로 업뎃되어 올라오는지 확인한다.**
    ![c567a9b9-e439-4b44-81a1-6ed555da06f5](https://raw.githubusercontent.com/is2js/screenshots/main/c567a9b9-e439-4b44-81a1-6ed555da06f5.gif)
