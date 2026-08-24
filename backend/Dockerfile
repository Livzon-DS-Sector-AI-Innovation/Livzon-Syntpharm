# Multi-stage Dockerfile for backend
# Stages: builder → runtime

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: builder — build stage with all dependencies
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Remove all existing Debian sources and use Chinese mirror
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/* && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# Install system dependencies required for OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager (use Alibaba PyPI mirror for speed)
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ uv==0.12.2

ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_EXTRA_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_PYTHON=/usr/local/bin/python3

# Copy and install Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime — production runtime (minimal image)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Remove all existing Debian sources and use Chinese mirror
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/* && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# Install only runtime system dependencies (no build tools)
RUN apt-get update && apt-get install -y \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code from builder
COPY --from=builder /app /app

EXPOSE 8000

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
