# OpenCode Platform - Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製源碼
COPY src/ ./src/
COPY .env.example ./.env.example

# 設置 Python 路徑
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# 創建數據目錄
RUN mkdir -p /app/data/documents /app/data/raw /app/data/users /app/data/audit /app/data/cost

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["uvicorn", "quitcode.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
