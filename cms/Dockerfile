FROM python:3.13-alpine
WORKDIR /app
COPY server.py /app/server.py
RUN addgroup -S -g 10001 app && adduser -S -D -H -u 10001 -G app app && mkdir -p /data && chown -R 10001:10001 /data /app
USER 10001:10001
EXPOSE 8090
CMD ["python","-u","server.py"]
