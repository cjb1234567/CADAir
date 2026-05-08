FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CADAIR_APP_ID=cadair_translate \
    CADAIR_OUTPUT_ROOT=/data/deliveries/apps \
    CADAIR_UPLOAD_ROOT=/data/uploads \
    CADAIR_ALLOWED_INPUT_ROOTS=/data/uploads,/data/document-intelligence,/data/deliveries \
    CADAIR_LOG_DIR=/data/deliveries/apps/cadair_translate/_logs \
    CADAIR_ODA_RUNTIME_DIR=/tmp/runtime-cadair \
    CADAIR_ODA_TIMEOUT_SECONDS=120

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xvfb \
        libgl1 \
        libglib2.0-0 \
        libxrender1 \
        libxext6 \
        libsm6 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/

RUN pip install --no-cache-dir \
        "aiohttp>=3.13.5" \
        "ezdxf>=1.4.3" \
        "fastapi>=0.110,<1" \
        "httpx>=0.27,<1" \
        "pydantic>=2,<3" \
        "python-dotenv>=1.2.2" \
        "uvicorn>=0.27,<1"

COPY cadair /app/cadair
COPY dwgtranslator /app/dwgtranslator

EXPOSE 8030

CMD ["uvicorn", "cadair.service:app", "--host", "0.0.0.0", "--port", "8030"]
