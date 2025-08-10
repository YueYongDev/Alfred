#!/bin/bash
# 停止 Alfred 数据导入任务

# Python 解释器
PYTHON_BIN="/home/yueyong/miniforge3/envs/alfred-ai/bin/python"

# 查找进程
PID=$(ps -ef | grep "$PYTHON_BIN -m scripts.import_personal_data" | grep -v grep | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "ℹ️ 没有找到正在运行的 Alfred 数据导入任务"
    exit 0
fi

# 停止进程
kill "$PID"

# 等待进程退出
sleep 1

if ps -p "$PID" > /dev/null; then
    echo "⚠️ 进程 $PID 未退出，执行强制终止"
    kill -9 "$PID"
fi

echo "✅ Alfred 数据导入任务已停止 (PID: $PID)"