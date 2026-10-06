FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    iptables \
    libcap2-bin \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Allow the non-root application user to manage only network firewall rules.
RUN setcap cap_net_admin+ep "$(readlink -f /usr/sbin/iptables)"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY wsgi.py .
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Run with gunicorn (optimized for heavy load)
# Workers: 2 per CPU core + 1
# Threads: for async handling
# Timeout: 120s for long-running tasks
# Max requests: recycle workers periodically to prevent memory leaks
CMD ["gunicorn", \
     "-w", "4", \
     "-b", "0.0.0.0:5000", \
     "--worker-class", "sync", \
     "--worker-tmp-dir", "/dev/shm", \
     "--timeout", "120", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--keep-alive", "65", \
     "--log-level", "info", \
     "wsgi:app"]
