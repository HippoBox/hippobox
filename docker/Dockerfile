# 1st stage: Frontend build (Node.js)
FROM node:22-slim AS frontend-builder
RUN apt-get update && apt-get upgrade -y && apt-get clean
WORKDIR /frontend
COPY src/frontend/package*.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

# 2nd stage: Backend build (Python)
FROM python:3.13-slim AS backend-builder
RUN apt-get update && apt-get upgrade -y && apt-get clean

WORKDIR /app
RUN pip install --no-cache-dir hatch uv

COPY README.md ./
COPY src/backend/ ./src/backend/
COPY --from=frontend-builder /frontend/dist/ ./src/backend/hippobox/static/dist/

WORKDIR /app/src/backend
RUN HIPPOBOX_SKIP_FRONTEND_BUILD=1 hatch build -t wheel
RUN uv export --frozen --no-dev --no-emit-project -o /app/requirements.txt

# 3rd stage: Final execution stage
FROM python:3.13-slim
RUN apt-get update && apt-get upgrade -y && apt-get clean
WORKDIR /app

COPY --from=backend-builder app/src/backend/dist/*.whl ./
COPY --from=backend-builder /app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --require-hashes -r requirements.txt && pip install --no-cache-dir --no-deps *.whl && rm *.whl requirements.txt

RUN groupadd --gid 10001 hippobox && useradd --uid 10001 --gid 10001 --create-home hippobox && mkdir -p /data/objects /data/qdrant && chown -R 10001:10001 /data /app
USER 10001:10001
ENV PYTHONUNBUFFERED=1 DB_NAME=/data/hippobox.db QDRANT_PATH=/data/qdrant OBJECT_STORAGE_LOCAL_ROOT=/data/objects
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)"
EXPOSE 8000

CMD ["uvicorn", "hippobox.server:app", "--host", "0.0.0.0", "--port", "8000"]
