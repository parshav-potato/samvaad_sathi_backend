# syntax=docker/dockerfile:1

# Pin to a specific patch for reproducibility. Update as needed.
FROM python:3.12.6-slim AS runtime

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
# For production hardening, consider:
# RUN useradd -m -u 10001 appuser \
#     && chown -R appuser:appuser /app
# USER appuser

CMD ["uvicorn", "src.main:backend_app", "--host", "0.0.0.0", "--port", "8000"]
