# ==============================================================================
# OmniSight Production Dockerfile
# Multi-stage production container for FastAPI Gateway & Playwright RPA Engine
# ==============================================================================

# Stage 1: Build & Python Dependency Resolution
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY automation/requirements.txt automation/
COPY backend/requirements.txt backend/

RUN pip install --user -r requirements.txt

# Stage 2: Production Runtime with Playwright Chromium
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.local/bin:$PATH" \
    PORT=8000 \
    APP_ENV=production

# Install runtime shared libraries required by headless Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

# Install Playwright browser binaries
RUN python -m playwright install chromium

# Copy application source code
COPY backend/ backend/
COPY automation/ automation/
COPY pytest.ini ./

# Ensure evidence artifact directories exist
RUN mkdir -p artifacts/runs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
