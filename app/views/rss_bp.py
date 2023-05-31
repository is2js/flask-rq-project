from flask import Blueprint, jsonify, render_template, abort
from flask_apispec import marshal_with, use_kwargs
from marshmallow import fields

from app import docs
from app.models import SourceCategory
from app.rss_sources import get_current_services, YoutubeService, BlogService, URLService
from app.views.base_view import BaseView
from app.utils import logger, grouped
from app.views.schemas import FeedListResponseSchema

rss_bp = Blueprint('rss', __name__, url_prefix='/rss')


class FeedListView(BaseView):
    # @use_kwargs(FeedListRequestSchema, location='query')
    @use_kwargs({'since': fields.Float(data_key='since')}, location='query')
    @marshal_with(FeedListResponseSchema)
    def get(self, since):
        try:
            feeds = []
            for service in get_current_services():
                feeds += service.get_feeds(since=since)

            # 통합feeds를 published 정순으로 정렬
            feeds.sort(key=lambda feed: feed.published)

            response = {
                'result_code': 'S-1',
                'message': '피드 조회 성공',
                'data': {'feeds': feeds},
                'category': 'All',
            }

            return response
        except Exception as e:
            return {'result_code': 400, 'message': str(e)}


class CategoryFeedListView(BaseView):
    @use_kwargs({'since': fields.Float(data_key='since')}, location='query')
    @marshal_with(FeedListResponseSchema)
    # path 파라미터는 @use_kwargs사용없이 인자로 바로 받는다.
    def get(self, category_name, since):
        try:
            if category_name == 'youtube':
                service = YoutubeService()
            elif category_name == 'blog':
                service = BlogService()
            elif category_name == 'url':
                service = URLService()
            else:
                raise ValueError(f'Invalid category name : {category_name}')

            feeds = service.get_feeds(since=since)

            # 역순으로 조회한 것을 정순 정렬 for front
            feeds.sort(key=lambda f: f.published_timestamp)

            response = {
                'result_code': 'S-1',
                'message': f'{category_name}의 피드들 조회 성공',
                'data': {
                    'feeds': feeds,
                },
                'category': category_name
            }

            return response
        except Exception as e:
            return {'result_code': 400, 'message': str(e)}


@rss_bp.errorhandler(422)
def error_handler(err):
    headers = err.data.get('headers', None)
    messages = err.data.get('messages', ['Invalid request'])

    logger.warning(f'Invalid input params: {messages}')

    if headers:
        return jsonify({'message': messages}), 400, headers
    else:
        return jsonify({'message': messages}), 400


FeedListView.register(rss_bp, docs, '/category/all', 'feedlistview')
CategoryFeedListView.register(rss_bp, docs, '/category/<category_name>', 'categoryfeedlistview')


@rss_bp.route('/categories')
def get_categories():
    try:
        categories_with_source_count_and_names = SourceCategory.get_list_with_source_count_and_names()
        # print(categories_with_source_count_and_names)
        rows = list(grouped(categories_with_source_count_and_names, 3))

        return render_template('/rss/categories.html', rows=rows)
    except Exception as e:
        logger.error(f'{str(e)}', exc_info=True)
        abort(422)


@rss_bp.route('/categories/all')
def get_all_feeds():
    # try:
    service_list = get_current_services()
    feeds = []
    for service in service_list:
        feeds += service.get_feeds()
    return render_template('/rss/feeds.html', feeds=feeds)


@rss_bp.route('/categories/<category_name>')
def get_feeds(category_name):
    # if category_name == 'youtube':
    #     service = YoutubeService()
    # elif category_name == 'blog':
    #     service = BlogService()
    # elif category_name == 'url':
    #     service = URLService()
    # else:
    #     raise ValueError(f'Invalid category name : {category_name}')

    # feeds = service.get_feeds()
    context = {
        # 'feeds' : service.get_feeds(),
        'category': category_name
    }

    return render_template('/rss/feeds.html', **context)

    # except Exception as e:
    #     logger.error(f'{str(e)}', exc_info=True)
    #     abort(422)

# @rss_bp.route('/main')
# def get_categories():
#     try:
#         feeds = []
#         for service in get_current_services():
#             feeds += service.get_feeds()
#
#         rows = list(grouped(feeds, 3))
#     except Exception as e:
#         logger.error(f'{str(e)}', exc_info=True)
#     try:
#         categories = SourceCategory.get_list_with_source_count()
#         print(categories)
#     except Exception as e:
#         logger.error(f'{str(e)}', exc_info=True)
#
#     return render_template('/rss/feeds.html', rows=rows)
