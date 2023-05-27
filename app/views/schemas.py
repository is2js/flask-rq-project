from marshmallow import Schema, fields, pre_dump


#### DOMAIN
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
    thumbnail_url = fields.String()
    category = fields.String()
    body = fields.String()

    # published = fields.DateTime(dump_only=True, format="%Y-%m-%d %H:%M:%S", timezone="Asia/Seoul")
    published_string = fields.String(dump_only=True)

    source_id = fields.Integer(required=True)


#### RESPONSE
class ResponseSchema(Schema):
    result_code = fields.String(required=True, data_key='resultCode')
    message = fields.String(required=True)


class FeedListResponseSchema(ResponseSchema):
    data = fields.Dict(
        values=fields.Nested(FeedSchema(), many=True, data_key="feeds")
    )

    count = fields.Integer()

    @pre_dump
    def compute_count(self, data, **kwargs):
        data['count'] = len(data['data']['feeds'])
        return data

