FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY ai_engine ./ai_engine
COPY execution ./execution
COPY edge_server ./edge_server
EXPOSE 8001
CMD ["uvicorn", "edge_server.edge:app", "--host", "0.0.0.0", "--port", "8001"]
