# 1. Base Image: Use the FULL version (Has GCC and Compilers pre-installed)
FROM python:3.12

ENV PYTHONUNBUFFERED=1
# 2. Install Audio Drivers
# We still need portaudio specifically for PyAudio, but GCC is already here.
RUN apt-get update && \
    apt-get install -y portaudio19-dev ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 3. Work Directory
WORKDIR /app

# 4. Copy Requirements
COPY requirements.txt .

# 5. Install Python Dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy Code
COPY . .

# 7. Run
CMD ["python", "DiscordBot.py"]