FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY ai_engine ./ai_engine
COPY execution ./execution
COPY cloud_server ./cloud_server
EXPOSE 8002
CMD ["uvicorn", "cloud_server.cloud:app", "--host", "0.0.0.0", "--port", "8002"]
