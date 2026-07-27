# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — AI Study Assistant (Django backend)
# Base: python:3.11-slim for a lightweight, production-grade image
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Prevent .pyc files and enable real-time log output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ─── System Dependencies ──────────────────────────────────────────────────────
# build-essential: needed for some Python C-extension packages (e.g. faiss-cpu)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Working Directory ────────────────────────────────────────────────────────
WORKDIR /app

# ─── Python Dependencies ──────────────────────────────────────────────────────
# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Application Code ────────────────────────────────────────────────────────
COPY . .

# ─── Port ────────────────────────────────────────────────────────────────────
EXPOSE 8000

# ─── Entrypoint ──────────────────────────────────────────────────────────────
# Runs migrations then starts the dev server (replace with gunicorn for production)
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
