FROM python:3.11-slim

LABEL maintainer="IBM Migration Copilot"
LABEL description="Advanced Assistance Service — ReAct agent at Human Review gate"

WORKDIR /service

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Environment defaults (override via docker-compose or k8s secrets)
ENV ASSISTANCE_PORT=8001
ENV ASSISTANCE_REDIS_URL=redis://redis:6379/0
ENV ASSISTANCE_QDRANT_HOST=qdrant
ENV ASSISTANCE_QDRANT_PORT=6333
ENV ASSISTANCE_MAIN_BACKEND_URL=http://backend:8000
ENV ASSISTANCE_LOG_LEVEL=info

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8001/health').raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info"]
