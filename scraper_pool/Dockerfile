# scraper_pool/Dockerfile  (context = repo root ".")
FROM python:3.12-slim
WORKDIR /app

# deps
COPY scraper_pool/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# code + plugins
COPY scraper_pool/worker.py .
COPY plugins/ ./plugins/

CMD ["python", "worker.py"]
