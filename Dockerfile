# =====================================================================
# PandaMIND Audio Scoring API — VPC Production Container
# Milestone M5: Offline Air-Gapped Deployment
# =====================================================================

FROM python:3.11-slim-bookworm AS runtime

LABEL maintainer="PandaMIND Content Trust Engineering" \
      version="1.0.0-rc1" \
      description="Offline Air-Gapped Audio Scoring API for Customer VPC"

# 1. Environment & Offline Hardening
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    SCORER_BACKEND="m3" \
    OFFLINE_MODE="true" \
    DATA_RESIDENCY_REGION="ap-south-1" \
    RETENTION_DAYS="7" \
    ZERO_RETENTION_MODE="false" \
    API_KEY_AUTH_ENABLED="false" \
    HOST="0.0.0.0" \
    PORT="8000"

WORKDIR /app

# 2. Install curl for container health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 3. Install Python Dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Source and Frozen Checkpoints
COPY src /app/src
COPY reports/checkpoints /app/reports/checkpoints
COPY data/manifests /app/data/manifests

# 5. Security Hardening: Unprivileged Execution
RUN groupadd -g 10001 pandamind && \
    useradd -u 10001 -g pandamind -s /bin/sh -m pandamind && \
    mkdir -p /app/tmp /app/reports/audit && \
    chown -R pandamind:pandamind /app

USER pandamind

# 6. Service Exposure & Health Check
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# 7. Production Serving Command
CMD ["uvicorn", "audio_detection.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
