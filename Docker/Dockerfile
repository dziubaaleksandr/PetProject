FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY Docker/requirements.txt /app/Docker/

RUN pip install --upgrade pip && pip install -r Docker/requirements.txt

COPY .. /app/
