FROM node:24-bookworm-slim AS web
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements-runtime-lock.txt ./
RUN pip install --no-cache-dir -r requirements-runtime-lock.txt && useradd --uid 1000 --create-home crawler && mkdir /data && chown crawler:crawler /data
COPY server/ server/
COPY server_entry.py ./
COPY --from=web /app/web/dist web/dist
USER crawler
ENV LAZYCRAWLER_DATA=/data
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health')"
CMD ["python","server_entry.py","--host","0.0.0.0"]
