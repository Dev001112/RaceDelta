# Dockerfile (Flask + optional Postgres via DATABASE_URL)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV OPENF1_BASE=https://api.openf1.org/v1
ENV OPENF1_TIMEOUT=10
ENV OPENF1_CACHE_TTL=300
ENV DATABASE_URL=sqlite:///racedelta.db
ENV PORT=8000

EXPOSE 8000
CMD ["python", "app.py"]
