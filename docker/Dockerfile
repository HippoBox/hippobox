# 1st stage: Frontend build (Node.js)
FROM node:20-slim AS frontend-builder
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
RUN pip install --no-cache-dir hatch

COPY README.md ./
COPY src/backend/ ./src/backend/
COPY --from=frontend-builder /frontend/dist/ ./src/backend/hippobox/static/dist/

WORKDIR /app/src/backend
RUN hatch build -t wheel

# 3rd stage: Final execution stage
FROM python:3.13-slim
RUN apt-get update && apt-get upgrade -y && apt-get clean
WORKDIR /app

COPY --from=backend-builder app/src/backend/dist/*.whl ./
RUN pip install --no-cache-dir *.whl && rm *.whl

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "hippobox.server:app", "--host", "0.0.0.0", "--port", "8000"]
