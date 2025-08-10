#!/bin/bash
# 启动 Alfred 数据导入任务（后台运行）

# 项目根目录
PROJECT_DIR="/home/yueyong/project/Alfred"
# Python 解释器
PYTHON_BIN="/home/yueyong/miniforge3/envs/alfred-ai/bin/python"
# 日志目录 & 文件
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/import_personal_data.out"

# 进入项目目录
cd "$PROJECT_DIR" || {
    echo "❌ 无法进入目录 $PROJECT_DIR"
    exit 1
}

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 启动任务
nohup "$PYTHON_BIN" -m scripts.import_personal_data \
    > "$LOG_FILE" 2>&1 &

PID=$!

echo "✅ Alfred 数据导入任务已启动"
echo "   PID: $PID"
echo "   日志: $LOG_FILE"
echo
echo "查看日志: tail -f $LOG_FILE"