FROM python:3.11-alpine

# 安装编译 psutil 所需依赖
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers procps

# 安装 psutil
RUN pip install --no-cache-dir psutil

COPY auto_keepalive.py /auto_keepalive.py

ENV TARGET_CPU=20
ENV TARGET_MEM=20

CMD ["python3", "/auto_keepalive.py"]
