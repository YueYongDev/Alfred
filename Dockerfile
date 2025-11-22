FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_SERVER_PORT=11435

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents tools server README.md ./

EXPOSE 11435

# DEV_RELOAD=true 开启 uvicorn 热重载（需挂载代码目录）
CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${API_SERVER_PORT:-11435} ${DEV_RELOAD:+--reload}"]
