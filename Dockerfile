FROM python:3.11-alpine

RUN apk add --no-cache procps

COPY auto_keepalive.py /auto_keepalive.py

ENV TARGET_CPU=20
ENV TARGET_MEM=20

CMD ["python3", "/auto_keepalive.py"]
