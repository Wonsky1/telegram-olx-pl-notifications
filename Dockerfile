FROM python:3.12-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

ARG BOT_TOKEN
ARG CHAT_IDS
ARG REDIS_HOST
ARG REDIS_PORT
ARG TOPN_DB_BASE_URL

ENV BOT_TOKEN=${BOT_TOKEN}
ENV CHAT_IDS=${CHAT_IDS}
ENV REDIS_HOST=${REDIS_HOST}
ENV REDIS_PORT=${REDIS_PORT}
ENV TOPN_DB_BASE_URL=${TOPN_DB_BASE_URL}

CMD ["python", "main.py"]
