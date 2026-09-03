# Flask API, sized for a 512MB / 0.1-CPU free instance.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV OPENF1_BASE=https://api.openf1.org/v1
ENV OPENF1_TIMEOUT=10
ENV OPENF1_CACHE_TTL=300
ENV DATABASE_URL=sqlite:////tmp/racedelta.db
ENV PORT=8000

# The baked .cache/ (16MB of precomputed JSON) is the whole point: a free instance
# sleeps after 15min idle and wakes with a blank fastf1_cache, so anything not
# already in .cache/ would refetch from the F1 API at 0.1 CPU.
ENV RACEDELTA_CACHE_DIR=/app/.cache
ENV FASTF1_CACHE_DIR=/tmp/fastf1_cache
# Past races never change; keep the baked entries fresh instead of rebuilding on every wake.
ENV RACEDELTA_CACHE_TTL=2592000
# Baked entries are up to 83 days past expiry; without a matching grace, 59 of the 294
# would refetch live. Historical F1 results don't change, so serving them stale is correct.
ENV RACEDELTA_CACHE_STALE_GRACE=31536000
# The startup warmer would fight the request that woke the instance for the same 0.1 CPU.
ENV RACEDELTA_WARM_CACHE=0

EXPOSE 8000
# 1 worker: each is ~200MB resident (pandas+scipy+fastf1+sklearn), so 2 would OOM 512MB.
# Threads instead, since the work is mostly waiting on the F1 API.
CMD gunicorn -b 0.0.0.0:$PORT -w 1 --threads 8 --timeout 180 app:app
