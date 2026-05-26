FROM python:3.13-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

FROM base AS detection
CMD ["python", "-m", "services.detection.consumer"]

FROM base AS risk-scoring
CMD ["python", "-m", "services.risk_scoring.consumer"]

FROM base AS routing
CMD ["python", "-m", "services.routing.consumer"]

FROM base AS analytics
CMD ["python", "-m", "services.analytics.consumer"]

FROM base AS api
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]