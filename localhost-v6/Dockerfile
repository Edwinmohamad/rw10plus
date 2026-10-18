FROM node:22-bookworm-slim
WORKDIR /app
COPY . .
RUN mkdir -p /app/data/uploads && chown -R node:node /app
USER node
ENV HOST=0.0.0.0 PORT=8097 DATA_DIR=/app/data
EXPOSE 8097
CMD ["node", "server.js"]
