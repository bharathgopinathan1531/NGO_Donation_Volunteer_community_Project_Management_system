FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

COPY . .
RUN useradd -m appuser && chown -R appuser /srv
USER appuser

EXPOSE 8000
# Apply migrations, make sure the super admin exists, then serve.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.create_super_admin && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
