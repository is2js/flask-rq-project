from datetime import datetime

from pytz import utc


def timedelta_to_remain(td):
    seconds = int(td.total_seconds())
    periods = [
        ('년', 60 * 60 * 24 * 365),
        ('월', 60 * 60 * 24 * 30),
        ('일', 60 * 60 * 24),
        ('시', 60 * 60),
        ('분', 60),
        ('초', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            # has_s = 's' if period_value > 1 else ''
            strings.append("%s%s" % (period_value, period_name))

    return "".join(strings) + " 남음"


def datetime_to_utc(_datetime: datetime):
    if not isinstance(_datetime, datetime):
        raise ValueError('datetime을 입력해주세요')

    return _datetime.astimezone(utc)
