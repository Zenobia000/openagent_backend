# OpenCode Platform Dockerfile
FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY pyproject.toml ./

# 安裝 Python 依賴
RUN pip install --no-cache-dir -e .

# 複製應用程式碼
COPY . .

# 建立資料目錄
RUN mkdir -p /app/data /app/logs

# 設置環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8001

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 啟動命令
CMD ["python", "-m", "api.main"]
