FROM python:3.12-slim
WORKDIR /app

COPY scheduler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy code + config
COPY scheduler/. .
COPY config/ config/

CMD ["python", "main.py"]