FROM python:3.9-slim-buster

ARG BOT_TOKEN
ARG CHAT_IDS
ARG URL

ENV BOT_TOKEN=$BOT_TOKEN
ENV CHAT_IDS=$CHAT_IDS
ENV URL=$URL

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
