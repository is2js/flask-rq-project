from flask import jsonify
from flask_apispec.views import MethodResource


class BaseView(MethodResource):

    @classmethod
    def register(cls, blueprint, docs, url, view_cls_name_lower):
        # 2. 해당url + name으로 bp에 view를 등록한다.
        blueprint.add_url_rule(url, view_func=cls.as_view(view_cls_name_lower))
        # 3. 공통 에러핸들링 422에러를 bp에 등록한다
        blueprint.register_error_handler(422, cls.handle_error)
        # 4. 해당bp이름으로 docs에 view class(기존 route view func)을 등록한다
        docs.register(cls, blueprint=blueprint.name)

    @staticmethod
    def handle_error(err):
        headers = err.data.get('headers', None)
        messages = err.data.get('messages', ['Invalid request'])
        if headers:
            return jsonify({'message': messages}), 400, headers
        else:
            return jsonify({'message': messages}), 400
