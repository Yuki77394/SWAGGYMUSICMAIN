FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ffmpeg \
        gcc \
        g++ \
        build-essential \
        libffi-dev \
        libssl-dev \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "SWAGGYMUSIC"]
