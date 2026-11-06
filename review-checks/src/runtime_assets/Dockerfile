FROM python:3.12-alpine@sha256:e064671ca452259bab50e8e2c7bd896e39e9a343bb06ca25234adf6fe18d0fc7

WORKDIR /opt/stack-review
COPY __init__.py fake_backend.py probe.py runtime_assets/
RUN adduser -D -H -u 10001 reviewer
USER reviewer
