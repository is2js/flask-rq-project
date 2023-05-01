- 참고: https://github1s.com/okpy/ok/blob/master/server/models.py#L52
### Tr
1. models.py에 init의 `from . import session`을 이용해서 작성한다.
    ```python
    def transaction(f):
        """ Decorator for database (session) transactions."""
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                value = f(*args, **kwargs)
                session.commit()
                return value
            except Exception:
                session.rollback()
                raise
        return wrapper
    ```
   
2. BaseModel에 적어둔 CRUD 메서드들을 @transaction을 이용해 수정한다.
   ```python
   class BaseModel(Base):
       __abstract__ = True
       @classmethod
       @transaction
       def get_list(cls):
           items = cls.query.all()
           # try:
           #     items = cls.query.all()
           #     session.close()
           # except Exception:
           #     session.rollback()
           #     raise
           return items
       
       @transaction
       def save(self):
           session.add(self)
           return self
           # try:
           #     session.add(self)
           #     session.commit()
           #     return self
           # except Exception:
           #     session.rollback()
           #     raise
       
       @transaction
       def update(self, **kwargs):
           for key, value in kwargs.items():
               setattr(self, key, value)
           return self
           # try:
           #     for key, value in kwargs.items():
           #         setattr(self, key, value)
           #     session.commit()
           #     return self
           # except Exception:
           #     session.rollback()
           #     raise
   
       @transaction
       def delete(self):
           session.delete(self)
           return self
           # try:
           #     session.delete(self)
           #     session.commit()
           # except Exception:
           #     session.rollback()
           #     raise
   ```
   

### Naming convention
3. `init.py`에서 `Base.metadata`를 Metadata()객체에 naming_convention=을 dict로 적용해서 새롭게 할당해준다.
   ```python
   Base = declarative_base()
   Base.query = session.query_property()
   # sqlite migrate 오류시 발생할 수 있는 버그 픽스
   naming_convention = {
       "ix": 'ix_%(column_0_label)s',
       "uq": "uq_%(table_name)s_%(column_0_name)s",
       "ck": "ck_%(table_name)s_%(column_0_name)s",
       "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
       "pk": "pk_%(table_name)s"
   }
   
   Base.metadata = MetaData(naming_convention=naming_convention)
   ```
   
4. sqlite db를 삭제하고 재생성한다.



### Pool options in Config
- 
1. Config에 `DATABASE_URL`환경변수 없을 조건으로
   1. db 주소
   2. pool 옵션들을 if else로 정의한 뒤 **init의 `create_engine()`에 갖다쓴다**
   ```python
   class Config:
       DATABASE_URL = os.getenv('DATABASE_URL') or 'sqlite:///db.sqlite'
       SQLALCHEMY_POOL_OPTIONS = {
           'pool_size': 3,
           'pool_recycle': 55,  # # ClearDB's idle limit is 90 seconds, so set the recycle to be under 90
           'pool_timeout': 5,
           'max_overflow': 10
       } if os.getenv('DATABASE_URL') else {
           'pool_size': 1,
           'max_overflow': 0
       }
   ```
   ```python
   # init.py
   
   # engine = create_engine("sqlite:///db.sqlite", pool_size=1, max_overflow=0) # default 5, 10
   engine = create_engine(Config.DATABASE_URL, **Config.SQLALCHEMY_POOL_OPTIONS)
   ```