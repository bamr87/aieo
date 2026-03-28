FROM python:3.12-slim

WORKDIR /app

# System dependencies for lxml and Playwright/Chromium
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libxml2-dev libxslt-dev ca-certificates \
        # Playwright/Chromium dependencies
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
        libpango-1.0-0 libcairo2 libasound2 libwayland-client0 \
        fonts-liberation fonts-noto-color-emoji && \
    rm -rf /var/lib/apt/lists/*

# Install only the packages the MCP server actually needs
COPY requirements-mcp.txt requirements-mcp.txt
RUN pip install --no-cache-dir -r requirements-mcp.txt

# Install Playwright browsers (chromium only)
RUN playwright install chromium

# Copy application code and prompts
COPY app/ app/
COPY prompts/ prompts/

# Healthcheck — just verify import works
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "from app.mcp_server import create_mcp_server; create_mcp_server()" || exit 1

# Default: run MCP server on stdio
CMD ["python", "-m", "app.mcp_server"]
