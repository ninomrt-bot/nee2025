# Dockerfile ─────────────────────────────────────────────────────
FROM python:3.11-slim

# dépendances compil C (opcua)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gunicorn prêt pour la prod (sinon `python app.py`)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]
