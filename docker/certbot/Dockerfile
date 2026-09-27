FROM alpine:3.22
RUN apk add --no-cache certbot openssl ca-certificates python3
COPY certificate.py /opt/certificate.py
COPY renew.sh /opt/renew.sh
ENTRYPOINT ["certbot"]
