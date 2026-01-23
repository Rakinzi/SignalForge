FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY api ./api

ENV DATABASE_URL=postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge
ENV PORT=8000

CMD ["uv", "run", "run-api"]
