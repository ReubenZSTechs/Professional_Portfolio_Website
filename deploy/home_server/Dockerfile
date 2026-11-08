# Optional self-hosting of the FastAPI backend (Vercel is the primary deployment).
# Build from the repo root:  docker build -f deploy/home_server/Dockerfile -t portfolio-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY backend/src ./backend/src
COPY content ./content
COPY knowledge ./knowledge
COPY backend/scripts ./backend/scripts

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/py/health')"
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
