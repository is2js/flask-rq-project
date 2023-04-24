import time
from urllib import request

from bs4 import BeautifulSoup


def count_words(url):
    print(f'Count words at {url}')
    start = time.time()

    r = request.urlopen(url)  # byte파일들 -> .read() 후 .decode() 필요

    soup = BeautifulSoup(r.read().decode(), "lxml")

    # 1) p태그를 찾아서 .text를 해온 뒤, 단어들처럼 공백으로 연결
    paragraphs = " ".join([p.text for p in soup.find_all("p")])
    # 2) dict에 단어 세기 -> 공백으로 모든 것을 쪼개서 단어로 세기
    word_count = dict()
    for i in paragraphs.split():
        if not i in word_count:
            word_count[i] = 1
        else:
            word_count[i] += 1

    end = time.time()

    time_elapsed = end - start

    print(word_count)
    print(f'Total words: {len(word_count)}')
    print(f'Time elapsed: {time_elapsed}')

    # return len(word_count)
    return word_count