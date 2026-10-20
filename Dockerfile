FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --system --uid 10001 --create-home appuser
COPY app ./app
RUN mkdir -p /srv/data && chown -R appuser:appuser /srv
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python -m app.seed && exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - app.wsgi:app"]
