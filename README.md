# Alfred (Agent Core)

精简版 Alfred，只保留多 Agent 编排和 OpenAI 兼容接口，适合直接挂接本地/远程 LLM 与若干常用工具。

## 项目结构
- `server/`：FastAPI OpenAI 兼容端点（`POST /v1/chat/completions`，支持流式/SSE、图片/文件）
- `agents/`：使用 qwen-agent 的路由编排，集成通用对话、视觉、代码、图片生成等子 Agent
- `tools/`：工具适配层（天气、热点榜、摘要、汇率、当前时间等）
- `requirements.txt`：运行依赖

## 环境变量
- `LLM_MODEL` / `LLM_VL_MODEL` / `LLM_CODE_MODEL` / `LLM_ROUTE_MODEL`：各模块使用的模型，默认使用 qwen 系列
- `LLM_BASE_URL`：OpenAI 兼容接口地址（Ollama 或第三方网关），默认 `http://127.0.0.1:11434/v1`
- `LLM_API_KEY`：接口密钥（Ollama 兼容接口可填任意非空值）
- `LLM_TEMPERATURE`：生成温度，默认 `0.3`
- `API_SERVER_PORT`：API 监听端口，默认 `11435`
- `DEV_RELOAD`：设为 `true` 时 uvicorn 开启热重载（Docker/本地均可用）
- `DAILY_HOT_API_BASE`：热点榜服务地址，供 `daily_hot_trends` 工具使用
- `WEB_SUMMARY_API`：文章摘要服务地址，供 `web_summary` 工具使用
- `EXCHANGE_RATE_API_KEY`：exchangerate-api.com 的 Key，供 `fx_rate` 使用
- 示例配置见 `.env.example`，可直接 `cp .env.example .env` 后按需修改填充密钥（推荐运行时用 `--env-file .env` 挂载）。

## 本地运行
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port ${API_SERVER_PORT:-11435} --reload
```

## Docker 使用
```bash
docker build -t alfred-core .
docker run --rm -p 11435:11435 \
  -e LLM_MODEL=qwen3:latest \
  -e LLM_BASE_URL=http://host.docker.internal:11434/v1 \
  -e LLM_API_KEY=ollama \
  -e DEV_RELOAD=true \
  --env-file .env \
  -v $(pwd):/app \
  alfred-core
```
- 一条命令完成构建与运行（如果本地还没有镜像）：
```bash
docker build -t alfred-core . \
  && docker run --rm -p 11435:11435 \
    --env-file .env \
    -e DEV_RELOAD=true \
    -v "$(pwd)":/app \
    alfred-core
```
- Linux 原生 Docker 访问宿主机服务时可加 `--add-host=host.docker.internal:host-gateway`。
- `API_SERVER_PORT` 可自定义；挂载代码目录可以配合 `DEV_RELOAD=true` 热重载。
- 环境变量推荐用 `--env-file .env`（可由 `.env.example` 复制调整）或逐个 `-e VAR=value` 传入，避免将敏感信息 bake 进镜像；如需固定写入镜像，可在 Dockerfile 中显式 `COPY .env /app/.env`。

## API 交互示例
向 `/v1/chat/completions` 发送 OpenAI Chat 兼容请求，支持 `stream=true`：
```bash
curl -X POST http://127.0.0.1:11435/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "stream": false,
    "messages": [
      {"role": "user", "content": "给我今天的天气和热点"}
    ]
  }'
```
请求体可携带 `messages[i].images` 或 `messages[i].files`，也可用 OpenAI 多模态的 `content` 数组。

## 内置工具
- `daily_hot_trends`：热点榜单，依赖 `DAILY_HOT_API_BASE`
- `web_summary`：文章摘要/标签，依赖 `WEB_SUMMARY_API`
- `fx_rate`：汇率查询，需 `EXCHANGE_RATE_API_KEY`
- `weather`：open-meteo 天气查询（无需 Key）
- `current_time`：当前时间（可指定时区）
- `WebSearch` / `CodeInterpreter`：来自 qwen-agent 的通用工具
