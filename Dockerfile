# AgenteQAPro Navigator — Chrome headless + MCP SSE server
# Build:  docker build -t agenteqa-navigator .
# Run:    docker run -p 8000:8000 agenteqa-navigator
# With key: docker run -p 8000:8000 -e MCP_API_KEY=secret agenteqa-navigator

FROM python:3.12-slim

# ── Chrome + dependencies ──────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    fonts-liberation \
    fonts-noto-color-emoji \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── App ───────────────────────────────────────────────────────────────────
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e ".[sse]"

# ── Chrome config ─────────────────────────────────────────────────────────
# Chromium path in Debian slim
ENV CHROME_EXECUTABLE=/usr/bin/chromium
# Required for Chrome in Docker (no kernel namespace sandbox)
ENV CHROME_EXTRA_ARGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new"

# ── Server config ─────────────────────────────────────────────────────────
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=3067
# Set MCP_API_KEY at runtime to enable auth: -e MCP_API_KEY=mysecret

EXPOSE 3067

# Health check — curl /health returns {"status":"ok"}
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3067/health')" || exit 1

CMD ["python", "-m", "agenteqa_navigator", "--transport", "sse"]
