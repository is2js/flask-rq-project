FROM eoranged/rq-dashboard:latest

# 환경변수 설정
ENV TZ=Asia/Seoul

# 시간대 설정
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone