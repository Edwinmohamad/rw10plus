FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RW10_DB_PATH=/app/data/rw10.db
WORKDIR /app
COPY server.py /app/server.py
COPY static /app/static
RUN mkdir -p /app/data && useradd --system --uid 10001 --home /app rw10 && chown -R rw10:rw10 /app/data
USER rw10
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
CMD ["python", "/app/server.py"]
