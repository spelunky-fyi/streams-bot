FROM python:3.9-slim-buster

COPY requirements.txt /streams-bot/
WORKDIR /streams-bot
RUN pip install -r requirements.txt
COPY . /streams-bot

ENTRYPOINT ["python", "streams-bot.py"]
CMD []
