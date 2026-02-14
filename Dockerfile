# 1. Base Image: Use the FULL version (Has GCC and Compilers pre-installed)
FROM python:3.12

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ---------- System dependencies ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        portaudio19-dev \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

# ---------- Workdir ----------
WORKDIR /app

# ---------- Install dependencies ----------
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---------- Copy project ----------
COPY . .

# ---------- Entrypoint ----------
CMD ["python", "-m", "bott.bot"]