from flask import Blueprint, jsonify, render_template, abort
from flask_apispec import marshal_with

from app import docs
from app.models import SourceCategory
from app.rss_sources import get_current_services
from app.views.base_view import BaseView
from app.utils import logger, grouped
from app.views.schemas import FeedListResponseSchema

rss_bp = Blueprint('rss', __name__, url_prefix='/rss')


class FeedListView(BaseView):
    # @use_kwargs({'from_id': fields.Int(required=True, data_key='fromId')}, location='query')
    # @use_kwargs(RoomListRequestSchema, location='query')
    @marshal_with(FeedListResponseSchema)
    def get(self):
        try:
            feeds = []
            for service in get_current_services():
                feeds += service.get_feeds()

            response = {
                'result_code': 'S-1',
                'message': '채팅방 조회 성공',
                'data': {'feeds': feeds},
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


FeedListView.register(rss_bp, docs, '/feeds', 'feedlistview')


@rss_bp.route('/main')
def get_categories():
    try:
        categories_with_source_count_and_names = SourceCategory.get_list_with_source_count_and_names()
        # print(categories_with_source_count_and_names)
        rows = list(grouped(categories_with_source_count_and_names, 3))

        return render_template('/rss/categories.html', rows=rows)
    except Exception as e:
        logger.error(f'{str(e)}', exc_info=True)
        abort(422)



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
