FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_SERVER_PORT=11435

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

COPY agents/ /app/agents/
COPY tools/ /app/tools/
COPY server/ /app/server/
COPY static/ /app/static/
COPY README.md /app/

EXPOSE 11435

# DEV_RELOAD=true 时开启 uvicorn 热重载；默认使用环境变量中的 API_SERVER_PORT
CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${API_SERVER_PORT:-11435} ${DEV_RELOAD:+--reload}"]
