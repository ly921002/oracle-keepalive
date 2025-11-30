# 使用轻量级的 Alpine Linux 作为基础镜像
FROM alpine:latest

# 安装 stress-ng (提供内存分配和更可控的 CPU 负载选项)
RUN apk update && apk add stress-ng

# 设置工作目录
WORKDIR /app

# 复制脚本到容器中
COPY keep_active.sh .

# 赋予脚本执行权限
RUN chmod +x keep_active.sh

# 定义容器启动时执行的命令
CMD ["/app/keep_active.sh"]
