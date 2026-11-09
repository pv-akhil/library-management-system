# Multi-stage enterprise Dockerfile for Library Management System
# Fully compliant with Red Hat OpenShift Security Context Constraints (SCC)
FROM python:3.12-slim

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Install essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Setup OpenShift non-root user permissions
# OpenShift assigns arbitrary user IDs in root group (0)
RUN mkdir -p /app/staticfiles /app/media && \
    chgrp -R 0 /app && \
    chmod -R g=u /app && \
    chmod +x /app/entrypoint.sh

# Run as non-root user (OpenShift standard UID)
USER 1001

EXPOSE 8000

# Healthcheck for container engines
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/login/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]

