import requests

from app.utils import parse_logger

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
}


# result_text = requests_url(self.headers, self.target_id, self._url)
# if not result_text:
#     return False

def requests_url(url, params=None):
    try:
        response = requests.get(url, headers=headers, params=params, timeout=3)
        # if response.status_code != 200:
        #     raise requests.HTTPError
        response.raise_for_status()  # Raises :class:`HTTPError`, if one occurred.
        return response.text
    except requests.exceptions.ReadTimeout:
        parse_logger.error(f'[ReadTimeout] requests 요청 실패( url: {url})', exc_info=True)
    except requests.HTTPError:
        parse_logger.error(f'[HTTPError] requests 요청 실패( url: {url})', exc_info=True)
    except requests.exceptions.ConnectionError:
        parse_logger.error(f'[ConnectionError] requests 요청 실패( url: {url})', exc_info=True)

    return False
