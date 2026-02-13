# OpenCode Sandbox - Python 執行環境
# 安全隔離的程式碼執行容器

FROM python:3.11-slim

LABEL maintainer="OpenCode Team"
LABEL description="Secure Python sandbox for code execution"

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MPLBACKEND=Agg

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 套件
RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pandas==2.2.0 \
    matplotlib==3.8.2 \
    seaborn==0.13.2 \
    scipy==1.12.0 \
    scikit-learn==1.4.0 \
    requests==2.31.0 \
    pillow==10.2.0 \
    openpyxl==3.1.2 \
    xlrd==2.0.1 \
    sympy==1.12

# 創建非 root 用戶
RUN useradd -m -s /bin/bash sandbox && \
    mkdir -p /app /output && \
    chown -R sandbox:sandbox /app /output

# 設定工作目錄
WORKDIR /app

# 複製執行腳本
COPY runner.py /app/runner.py

# 切換到非 root 用戶
USER sandbox

# 預設命令
ENTRYPOINT ["python", "/app/runner.py"]
