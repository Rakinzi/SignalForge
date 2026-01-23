FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY detector ./detector

ENV REDIS_ADDR=redis:6379
ENV REDIS_STREAM=flows
ENV DATABASE_URL=postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge

CMD ["uv", "run", "run-detector"]
