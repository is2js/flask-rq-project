#### CREATE IMAGE SET ####
import os

from PIL import Image
import time


def create_image_set(image_dir, image_name):
    start = time.time()

    # 각 최소 px 사이즈를 미리 정해놓는다.
    size_map = dict(
        thumbnail=(35, 35),
        small=(540, 540),
        medium=(768, 768),
        large=(992, 992),
        xl=(1200, 1200),
        xxl=(1400, 1400),
    )

    # file -> image객체를 만든다.
    image = Image.open(os.path.join(image_dir, image_name))

    # 각 save 전 이름 뒤에 "-size"를 적어줘야하기 때문에 ext(확장자)이름을 미리 빼놓는다.
    # image_ext = image_name.split('.')[-1]
    # -> image_ext에는 .png처럼 dot이 맨앞에 포함되어있다.
    image_name, image_ext = os.path.splitext(image_name)

    # 각 image객체를 사이즈별ㄹ .copy()부터 한 뒤, .thumbnail()메서드로 resize 후 .save()까지 한다.
    # thumbnail_image = image.copy()
    # thumbnail_image.thumbnail(size_map['thumbnail'], Image.LANCZOS)  # replace함수
    # thumbnail_image.save(f'{os.path.join(image_dir, image_name)}-thumbnail.{image_ext}',
    #                      optimize=True, quality=95)

    result = dict()

    for size_name, size in size_map.items():
        copied_image = image.copy()
        copied_image.thumbnail(size, Image.LANCZOS)  # replace함수
        copied_image.save(f'{os.path.join(image_dir, image_name)}-{size_name}{image_ext}',
                          optimize=True, quality=95)

        result[size_name] = f'{os.path.join(image_dir, image_name)}-{size_name}{image_ext}'

    end = time.time()

    time_elapsed = end - start

    print(f'Task complete in: {time_elapsed}')

    return result
