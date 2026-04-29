# Imagen de producción para la API FastAPI (VPS, registry o orquestador con Docker).
# Build:  docker build -t portfolio-api:latest .
# Run:   docker run --rm -p 8000:8000 --env-file .env portfolio-api:latest
# Compose: docker compose -f docker-compose.prod.yml up -d --build
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Usuario sin privilegios: mitiga fuga si el proceso queda comprometido
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home /app --shell /usr/sbin/nologin app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R app:app /app

USER app

EXPOSE 8000

# Sin --reload. start-period: margen para init_db si Postgres ya está en red.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
