FROM python:3.11-alpine

WORKDIR /usr/src/app

RUN apk add build-base

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

LABEL org.opencontainers.image.source https://github.com/SENERGY-Platform/analytics-flow-repo

CMD [ "python", "-u", "./main.py" ]
