import re

def slugify(value):
    value = re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ-]', '', value).strip().lower()
    value = re.sub(r'[-\s]+', '-', value)
    return value
