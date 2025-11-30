FROM alpine:3.20

RUN apk add --no-cache curl bash

WORKDIR /app

COPY keepalive.sh /app/keepalive.sh
RUN chmod +x /app/keepalive.sh

ENV TARGET_URL="https://www.google.com/generate_204"
ENV INTERVAL=30

CMD ["bash", "/app/keepalive.sh"]
