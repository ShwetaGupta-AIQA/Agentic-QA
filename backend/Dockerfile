FROM python:3.12-slim AS dependencies
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 LANGGRAPH_STRICT_MSGPACK=true
WORKDIR /app
COPY backend/requirements.lock.txt /tmp/requirements.lock.txt
RUN pip install --no-cache-dir -r /tmp/requirements.lock.txt
RUN useradd --uid 10001 --create-home qa && mkdir -p /app/reports /app/.chroma && chown -R qa:qa /app/reports /app/.chroma
FROM dependencies AS browser-dependencies
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/qa-browsers
RUN playwright install --with-deps chromium && chmod -R a+rX /opt/qa-browsers
FROM dependencies AS api
COPY backend /app/backend
COPY data /app/data
COPY automation /app/automation
COPY sut /app/sut
USER qa
WORKDIR /app/backend
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=3)"
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8001","--no-access-log"]
FROM browser-dependencies AS worker
COPY backend /app/backend
COPY data /app/data
COPY automation /app/automation
COPY sut /app/sut
USER qa
WORKDIR /app/backend
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "from pathlib import Path; import time; assert time.time()-Path('/tmp/qa-worker-heartbeat').stat().st_mtime<240"
CMD ["python","-m","app.worker"]
