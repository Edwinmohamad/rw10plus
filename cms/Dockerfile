FROM python:3.13-alpine
WORKDIR /app
COPY server.py /app/server.py
RUN addgroup -S app && adduser -S app -G app && mkdir -p /data && chown app:app /data
USER app
EXPOSE 8090
CMD ["python","-u","server.py"]
