# Imagem única: compila o frontend e serve tudo pelo FastAPI na porta 8000.
#   docker build -t semprehub .
#   docker run -p 8000:8000 --env-file .env semprehub

# 1) Frontend
FROM public.ecr.aws/docker/library/node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) Backend
FROM public.ecr.aws/docker/library/python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SEMPREHUB_AMBIENTE=producao \
    SEMPREHUB_FRONTEND_DIST=/app/frontend/dist \
    DATABASE_URL=sqlite:////app/dados/semprehub.db
WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY --from=frontend /app/frontend/dist /app/frontend/dist

RUN useradd --create-home semprehub && mkdir -p /app/dados && chown semprehub /app/dados \
    && chmod -R a+rX /app/backend /app/frontend/dist
USER semprehub
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
