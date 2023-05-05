from datetime import datetime

from app.utils import timedelta_to_remain


def remain_from_now(_datetime):
    diff_timedelta = _datetime - datetime.now()
    return timedelta_to_remain(diff_timedelta)
