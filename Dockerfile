FROM python:3.11-slim

# Устанавливаем системные пакеты (ffmpeg, libreoffice)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libreoffice \
    libreoffice-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Выводим версии для проверки в логах сборки
RUN ffmpeg -version || echo "FFmpeg not found" && \
    libreoffice --version || echo "LibreOffice not found"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "converter_bot.py"]
