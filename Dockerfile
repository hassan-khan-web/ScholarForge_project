FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requires.txt .

RUN pip install --no-cache-dir -r requires.txt

COPY . .

EXPOSE 5000