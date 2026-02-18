FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements_api.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements_api.txt

COPY . .

CMD ["python", "-m", "bott.bot"]
