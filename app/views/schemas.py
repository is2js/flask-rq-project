from marshmallow import Schema, fields, pre_dump


#### DOMAIN
class SourceCategorySchema(Schema):
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True, index=True)
    """
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True)


class SourceSchema(Schema):
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)  # 사용자입력 NAME ex> Tistory, Naver, 유튜브, 왓챠
    url = db.Column(db.Text, nullable=False)
    target_name = db.Column(db.Text, nullable=False)  # RSS타겟 NAME ex> xxx님의 blog, 쌍보네TV
    target_url = db.Column(db.Text, nullable=False, index=True, unique=True)

    source_category_id = db.Column(db.Integer, db.ForeignKey('sourcecategory.id', ondelete="CASCADE"))
    source_category = relationship('SourceCategory', foreign_keys=[source_category_id], back_populates='sources',
                                   uselist=False)

    feeds = relationship('Feed', back_populates='source', cascade='all, delete-orphan')
    """
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True)
    url = fields.String(required=True)
    target_name = fields.String(required=True, data_key='targetName')
    target_url = fields.String(required=True, data_key='targetUrl')
    thumbnail_url = fields.String(data_key='thumbnailUrl')

    source_category = fields.Nested(SourceCategorySchema(), data_key='sourceCategory')


class FeedSchema(Schema):
    """
    class Feed(BaseModel):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.Text, nullable=False)
        url = db.Column(db.Text, nullable=False, index=True)
        thumbnail_url = db.Column(db.Text, nullable=True)
        category = db.Column(db.Text, nullable=True)
        body = db.Column(db.Text, nullable=True)
        published = db.Column(db.DateTime(timezone=True))
        published_string = db.Column(db.Text, nullable=True)

        source_id = db.Column(db.Integer, db.ForeignKey('source.id', ondelete="CASCADE"))
        source = relationship('Source', foreign_keys=[source_id], back_populates='feeds', uselist=False)
    """
    id = fields.Integer(dump_only=True)
    title = fields.String(required=True)
    url = fields.String(required=True)
    thumbnail_url = fields.String(data_key='thumbnailUrl')
    category = fields.String()
    body = fields.String()

    # published = fields.DateTime(dump_only=True, format="%Y-%m-%d %H:%M:%S", timezone="Asia/Seoul")
    published_string = fields.String(dump_only=True, data_key='publishedString')

    # source_id = fields.Integer(required=True)
    source = fields.Nested(SourceSchema())

    published_timestamp = fields.Method("get_published_timestamp", data_key='publishedTimestamp')

    def get_published_timestamp(self, obj):
        # obj는 직렬화할 Feed 인스턴스입니다.
        # @property로 정의해놓은 published_timestamp 값을 반환합니다.
        return obj.published_timestamp


#### RESPONSE
class ResponseSchema(Schema):
    result_code = fields.String(required=True, data_key='resultCode')
    message = fields.String(required=True)


class FeedListResponseSchema(ResponseSchema):
    data = fields.Dict(
        values=fields.Nested(FeedSchema(), many=True, data_key="feeds")
    )

    count = fields.Integer(dump_only=True)

    category = fields.Str(dump_only=True)

    @pre_dump
    def compute_count(self, data, **kwargs):
        if data.get('data'):
            data['count'] = len(data['data']['feeds'])
        else:
            data['count'] = 0
        return data
