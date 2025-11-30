#!/bin/bash

# --- Docker 容器内的配置参数 ---
# 这个脚本将是容器的入口点 (CMD)。

# 1. CPU 负载配置
# --cpu 1: 使用 1 个 vCPU 核心。
# --cpu-method matrixprod: 使用矩阵乘法，这是一个持续且稳定的 CPU 负载方法。
# --timeout 0: 保持 CPU 负载进程持续运行，直到容器停止。
CPU_LOAD_CORES=1

# 2. 内存负载配置
# --vm 1: 使用 1 个内存分配进程。
# --vm-bytes 2G: 分配 2GB 内存。 (请根据您的Arm VPS总内存调整，通常 24GB)
# --vm-keep: 保持内存分配，不释放。
# --timeout 0: 保持内存分配进程持续运行。
MEM_ALLOC_BYTES="2G"
MEM_LOAD_PROCESSES=1

# -----------------------------------

echo "--- 启动 OCI VPS 活跃保持 Docker 容器负载 ---"
echo "配置: CPU 核数=${CPU_LOAD_CORES}, 内存=${MEM_ALLOC_BYTES}"

# 启动 stress-ng 进程
# 同时运行 CPU 和 VM (内存) 压力测试，使其持续运行 (timeout 0)
stress-ng \
    --cpu $CPU_LOAD_CORES \
    --cpu-method matrixprod \
    --vm $MEM_LOAD_PROCESSES \
    --vm-bytes $MEM_ALLOC_BYTES \
    --vm-keep \
    --timeout 0

# 保持容器持续运行（虽然 stress-ng 已经设置了 --timeout 0，但这是防止意外终止的备用）
tail -f /dev/null
