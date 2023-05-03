FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 환경변수 설정
ENV TZ=Asia/Seoul
# 시간대 설정
# RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

#COPY . /app
#WORKDIR /app

# add requirements.txt to the image
ADD ./requirements.txt /app/requirements.txt

# set working directory to /app/
WORKDIR /app

# install python dependencies
#RUN pip install -r requirements.txt

RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt --root-user-action=ignore && \
    rm -rf /root/.cache/pip && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone