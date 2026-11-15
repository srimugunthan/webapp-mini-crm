# --- build the React SPA
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- run the API (and serve the built SPA)
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY --from=web /web/dist ./static
RUN useradd --create-home --uid 10001 crm && mkdir -p /db /data && chown -R crm /db /data
USER crm
ENV DB_PATH=/db/crm.sqlite DATA_DIR=/data STATIC_DIR=/app/static PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"
# one worker: SQLite file with WAL (decision D21)
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
