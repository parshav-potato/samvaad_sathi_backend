# syntax=docker/dockerfile:1

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal OS deps (curl for healthchecks)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

EXPOSE 8000

# Note: Running as root by default to avoid volume permission issues on Windows bind mounts.
# For production hardening, create a non-root user and chown /app and /app/uploads accordingly.

CMD ["uvicorn", "src.main:backend_app", "--host", "0.0.0.0", "--port", "8000"]
