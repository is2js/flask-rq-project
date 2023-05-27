import os
from itertools import zip_longest
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("./.env")



class SourceConfig:
    ## TITLE LEVEL
    TITLE_LEVEL = os.getenv('TITLE_LEVEL', None) or "###"

    ## BLOG
    BLOG_TITLE = os.getenv('BLOG_TITLE', None) or "📚 최근 블로그"

    blog_display_numbers_or_none = os.getenv('BLOG_DISPLAY_NUMBERS', None)
    BLOG_DISPLAY_NUMBERS = int(blog_display_numbers_or_none) if blog_display_numbers_or_none else 10

    # TISOTRY
    tistory_target_ids = [item.strip() for item in os.getenv('TISTORY_TARGET_IDS').split(',') if item]
    tistory_categories = [item.strip() if item else None for item in os.getenv('TISTORY_CATEGORIES').split(',')]
    tistory_target_id_and_categories = list(zip_longest(tistory_target_ids, tistory_categories)) if tistory_target_ids else []
    # print(tistory_target_id_and_categories) # [('nittaku', None)] # [(None, None)]

    # NAVER
    naver_target_ids = [item.strip() for item in os.getenv('NAVER_TARGET_IDS').split(',') if item]
    naver_categories = [item.strip() if item else None for item in os.getenv('NAVER_CATEGORIES').split(',')]
    naver_target_id_and_categories = list(zip_longest(naver_target_ids, naver_categories)) if naver_target_ids else []
    # print(naver_targets) # [('is2js', None)]

    ## YOUTUBE
    YOUTUBE_TITLE = os.getenv('YOUTUBE_TITLE', None) or "🎞 최근 유튜브"

    youtube_display_numbers_or_none = os.getenv('YOUTUBE_DISPLAY_NUMBERS', None)
    YOUTUBE_DISPLAY_NUMBERS = int(youtube_display_numbers_or_none) if youtube_display_numbers_or_none else 10

    youtube_target_ids = [item.strip() for item in os.getenv('YOUTUBE_TARGET_IDS').split(',') if item]

    ## URL
    URL_TITLE = os.getenv('URL_TITLE', None) or "📆 관심 RSS 구독"
    URL_DISPLAY_NUMBERS = int(os.getenv('URL_DISPLAY_NUMBERS', None)) or 10

    urls = [item.strip() for item in os.getenv('URL_LIST').split(',') if item]
    url_names = [item.strip() for item in os.getenv('URL_NAME').split(',') if item]
    url_and_names = list(zip(urls, url_names)) if urls else []


    # log폴더 설정
    BASE_FOLDER = Path(__file__).resolve().parent  # BASE_FOLDER:  /계정명/rss_sources
    LOG_FOLDER = BASE_FOLDER.parent.joinpath('logs')  # LOG_FOLDER:  /계정명 + logs


    # DB 설정
    DATABASE_URL = os.getenv('DATABASE_URL') or 'sqlite:///db.sqlite'
    SQLALCHEMY_POOL_OPTIONS = {
        'pool_size': 3,
        'pool_recycle': 55,  # # ClearDB's idle limit is 90 seconds, so set the recycle to be under 90
        'pool_timeout': 5,
        'max_overflow': 10
    }