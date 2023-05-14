import os
from itertools import zip_longest

from dotenv import load_dotenv

load_dotenv()


class SourceConfig:
    ## TITLE LEVEL
    TITLE_LEVEL = os.getenv('TITLE_LEVEL', None) or "###"

    ## BLOG
    BLOG_TITLE = os.getenv('BLOG_TITLE', None) or "📚 최근 블로그"

    blog_display_numbers_or_none = os.getenv('BLOG_DISPLAY_NUMBERS', None)
    BLOG_DISPLAY_NUMBERS = int(blog_display_numbers_or_none) if blog_display_numbers_or_none else 5

    # TISOTRY
    tistory_target_ids = [item.strip() if item else None for item in os.getenv('TISTORY_TARGET_IDS').split(',')]
    tistory_categories = [item.strip() if item else None for item in os.getenv('TISTORY_CATEGORIES').split(',')]
    tistory_target_id_and_categories = list(zip_longest(tistory_target_ids, tistory_categories))
    # print(tistory_targets) # [('nittaku', None)] # [(None, None)]

    # NAVER
    naver_target_ids = [item.strip() if item else None for item in os.getenv('NAVER_TARGET_IDS').split(',')]
    naver_categories = [item.strip() if item else None for item in os.getenv('NAVER_CATEGORIES').split(',')]
    naver_target_id_and_categories = list(zip_longest(naver_target_ids, naver_categories))
    # print(naver_targets) # [('is2js', None)]

    ## YOUTUBE
    YOUTUBE_TITLE = os.getenv('YOUTUBE_TITLE', None) or "🎞 최근 유튜브"

    youtube_display_numbers_or_none = os.getenv('YOUTUBE_DISPLAY_NUMBERS', None)
    YOUTUBE_DISPLAY_NUMBERS = int(youtube_display_numbers_or_none) if youtube_display_numbers_or_none else 5

    youtube_target_ids = [item.strip() if item else None for item in os.getenv('YOUTUBE_TARGET_IDS').split(',')]

    ## URL
    URL_TITLE = os.getenv('URL_TITLE', None) or "📆 관심 RSS 구독"
    URL_DISPLAY_NUMBERS = int(os.getenv('URL_DISPLAY_NUMBERS', None)) or 5

    urls = [item.strip() if item else None for item in os.getenv('URL_LIST').split(',')]
    url_names = [item.strip() if item else None for item in os.getenv('URL_NAME').split(',')]
    url_and_names = list(zip(urls, url_names))
