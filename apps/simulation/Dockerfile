FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=contracts . /packages/strategy-contracts
COPY requirements.txt .

RUN pip install --no-cache-dir /packages/strategy-contracts -r requirements.txt

COPY app ./app

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /usr/sbin/nologin -M appuser && \
    chown -R appuser:appgroup /app
USER 10001:10001

EXPOSE 8081

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8081}
