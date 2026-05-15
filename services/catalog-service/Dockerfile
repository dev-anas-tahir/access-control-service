FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY packages/ /packages/

RUN uv sync --no-dev

COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
