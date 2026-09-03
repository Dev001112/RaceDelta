# Dockerfile (Flask + optional Postgres via DATABASE_URL)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV OPENF1_BASE=https://api.openf1.org/v1
ENV OPENF1_TIMEOUT=10
ENV OPENF1_CACHE_TTL=300
ENV DATABASE_URL=sqlite:////data/racedelta.db
ENV PORT=8000

# Mount a persistent volume at /data: fastf1 session files and the JSON cache
# are expensive to rebuild (minutes per season) and must survive restarts.
ENV FASTF1_CACHE_DIR=/data/fastf1_cache
ENV RACEDELTA_CACHE_DIR=/data/.cache
RUN mkdir -p /data/fastf1_cache /data/.cache

EXPOSE 8000
# 2 workers x 4 threads: fastf1 loads block for tens of seconds, so threads matter more than workers.
CMD gunicorn -b 0.0.0.0:$PORT -w 2 --threads 4 --timeout 180 app:app
