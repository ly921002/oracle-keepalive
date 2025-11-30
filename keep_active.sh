#!/bin/sh
# keep_active.sh - 通用负载脚本

# --- 接收环境变量，设置默认值（如果未定义） ---

# 1. CPU 负载配置
# 设置用于产生负载的 CPU 核心数
CPU_LOAD_CORES=${CPU_LOAD_CORES:-1}  

# 2. 内存负载配置
# 设置要分配的内存大小 (例如: 700M, 1500M, 2G)
MEM_ALLOC_BYTES=${MEM_ALLOC_BYTES:-700M}
MEM_LOAD_PROCESSES=1 # 保持为 1 个进程来分配内存

# -----------------------------------
echo "--- 节奏负载模式已启动 ---"
echo "CPU 核心: $CPU_LOAD_CORES"
echo "基础内存: $MEM_ALLOC_BYTES"

while true; do
    # 工作时间：120~300 秒（2~5 分钟）
    WORK=$(( RANDOM % 180 + 120 ))

    # 休息时间：15~35 秒
    REST=$(( RANDOM % 20 + 15 ))

    # CPU 负载：10%~15%
    CPU_LOAD=$(( RANDOM % 5 + 10 ))

    echo "[工作] CPU=${CPU_LOAD}% 内存=${MEM_ALLOC_BYTES} 持续 ${WORK}s"

    # 启动 stress-ng 负载（自动结束）
    stress-ng \
        --cpu "$CPU_LOAD_CORES" \
        --cpu-load "$CPU_LOAD" \
        --vm 1 \
        --vm-bytes "$MEM_ALLOC_BYTES" \
        --vm-keep \
        --timeout "$WORK" &

    # 等待当前 stress 进程结束，避免重叠
    wait $!

    echo "[休息] ${REST}s"
    sleep $REST
done

