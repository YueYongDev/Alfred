#!/bin/bash
set -e

# 项目根目录
PROJECT_ROOT="/home/yueyong/project/Alfred"
cd "$PROJECT_ROOT"

# 日志目录
mkdir -p "$PROJECT_ROOT/logs"

PYTHON_BIN="/home/yueyong/miniforge3/envs/alfred-ai/bin/python"

# 第一个分片：绑定 11434 端口的 Ollama
echo "启动分片 0 ..."
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
OLLAMA_EMBEDDING_URL=http://127.0.0.1:11434 \
"$PYTHON_BIN" -m rag_engine.light_rag.build_index --shard 0 --shards 2 \
  > logs/index_shard0.log 2>&1 &

# 第二个分片：绑定 11435 端口的 Ollama
echo "启动分片 1 ..."
OLLAMA_BASE_URL=http://127.0.0.1:11435 \
OLLAMA_EMBEDDING_URL=http://127.0.0.1:11435 \
"$PYTHON_BIN" -m rag_engine.light_rag.build_index --shard 1 --shards 2 \
  > logs/index_shard1.log 2>&1 &

echo "✅ 两个索引进程已启动，日志在 logs/index_shard*.log"