#!/bin/sh
# keep_active.sh - 通用负载脚本

# --- 接收环境变量，设置默认值（如果未定义） ---

# 1. CPU 负载配置
# 设置用于产生负载的 CPU 核心数
CPU_LOAD_CORES=${CPU_LOAD_CORES:-1} 

# 设置 CPU 目标总负载百分比。
# 例如，设置为 20，表示所有核心的总负载目标为 20%。
CPU_LOAD_PERCENT=${CPU_LOAD_PERCENT:-20} 

# 2. 内存负载配置
# 设置要分配的内存大小 (例如: 700M, 1500M, 2G)
MEM_ALLOC_BYTES=${MEM_ALLOC_BYTES:-512M}
MEM_LOAD_PROCESSES=1 # 保持为 1 个进程来分配内存

# -----------------------------------

echo "--- 启动 OCI VPS 活跃保持 Docker 容器负载 ---"
echo "配置: CPU 核数=${CPU_LOAD_CORES}, 目标总负载=${CPU_LOAD_PERCENT}%, 内存=${MEM_ALLOC_BYTES}"

# 使用 stress-ng 同时运行 CPU 和 VM (内存) 压力测试
stress-ng \
    --cpu $CPU_LOAD_CORES \
    --cpu-method matrixprod \
    --cpu-load $CPU_LOAD_PERCENT \
    --vm $MEM_LOAD_PROCESSES \
    --vm-bytes $MEM_ALLOC_BYTES \
    --vm-keep \
    --timeout 0

# 保持容器持续运行
tail -f /dev/null
