runserver:
    uv run uvicorn app.main:app --reload

makemigrations message:
    alembic revision --autogenerate -m {{message}}

migrate:
    alembic upgrade head
