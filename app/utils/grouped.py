import itertools


def grouped(iterable, n, strict=False, fill_value=None):
    if strict and len(iterable) % n != 0:
        raise ValueError('그룹별 갯수가 정확하지 않습니다.')

    # 1) zip에 iter()로 만든 것을 그룹내갯수만큼 zip 집어넣으면, 1개씩 빠져서 조합되어
    #    group이 형성된다. 그 갯수만큼 list로 복사한 뒤, -> zip()괄호안에 *args로 풀어준다.
    #    -> 왜냐면 zip은 콤마로 그 인자들을 받는 메서드이므로
    args = [iter(iterable)] * n
    # 2) 나누어떨어지는 경우, zip에다가 iter를 그룹화갯수만큼 comma로 연결한다.
    if strict:
        return zip(*args)
    # 3) 나누어떨어지지 않는 경우 .itertools.zip_longest에 넣어준다.
    else:
        return itertools.zip_longest(*args, fillvalue=fill_value)