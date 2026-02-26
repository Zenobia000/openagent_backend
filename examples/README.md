# OpenCode Platform - 範例程式碼

本目錄包含展示 OpenCode Platform 主要功能的實用範例。

## 📋 快速開始

### 前置需求

1. **Python 3.11+** 已安裝
2. **uv** 已安裝
3. **相依套件已安裝**：`uv pip install -e ".[dev]"`
4. **API Keys** 已在 `.env` 中設定

### 設定

```bash
# 從專案根目錄
cd opencode_backend

# 安裝 uv（如尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 建立虛擬環境並安裝
uv venv --python 3.11
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

uv pip install -e ".[dev]"

# 確認 .env 檔案存在並包含 API keys
cp .env.example .env
# 編輯 .env 並新增你的 keys
```

### 安裝選項

| 安裝指令 | 用途 |
|---------|------|
| `uv pip install -e ".[dev]"` | 開發環境（測試、linting） |
| `uv pip install -e ".[production]"` | 生產環境（含 Anthropic、Gemini、Knowledge） |
| `uv pip install -e ".[all]"` | 全部功能（生產 + 開發 + EasyOCR） |
| `uv pip install -e ".[anthropic]"` | 僅 Anthropic LLM |
| `uv pip install -e ".[google]"` | 僅 Gemini LLM |
| `uv pip install -e ".[knowledge]"` | 文件解析（PyMuPDF、docx、pandas） |
| `uv pip install -e ".[docling]"` | Docling（含 torch/CUDA，很大） |
| `uv pip install -e ".[easyocr]"` | EasyOCR（含 PyTorch，約 2GB） |

---

## 📚 範例

### 1. 簡單聊天 (`simple_chat.py`)

**展示內容：**
- 基本引擎初始化
- Auto 模式路由（System 1 vs System 2）
- 明確模式選擇
- 上下文傳遞

**執行：**
```bash
python examples/simple_chat.py
```

**預期輸出：**
```
🚀 Initializing OpenCode Platform...
✅ Engine initialized

============================================================
Example 1: Simple Chat (Auto → System 1)
============================================================
Query: What is machine learning?

Selected Mode: chat
Cognitive Level: system1
Response:
Machine learning is a subset of artificial intelligence...
```

**學習重點：**
- Router 如何分類查詢複雜度
- System 1（快速）與 System 2（分析）的差異
- 基本請求/回應處理

---

### 2. 程式碼沙箱 (`code_sandbox.py`)

**展示內容：**
- 安全的程式碼生成與執行
- Docker 沙箱隔離
- 演算法實作
- 沙箱內檔案操作

**執行：**
```bash
python examples/code_sandbox.py
```

**前置需求：**
- Docker 已安裝且執行中
- 足夠的權限執行 Docker 容器

**預期輸出：**
```
🚀 Code Sandbox Examples

============================================================
Example 1: Simple Calculation
============================================================
Response:
Here's a factorial function:

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Test
print(factorial(5))  # Output: 120
```

**學習重點：**
- 程式碼生成工作流程
- 沙箱安全功能
- 程式碼執行中的錯誤處理

---

### 3. 多供應商 (`multi_provider.py`)

**展示內容：**
- 多供應商備援鏈
- 自動錯誤重試
- 成本最佳化策略
- 錯誤分類（可重試 vs 不可重試）

**執行：**
```bash
python examples/multi_provider.py
```

**前置需求：**
- 至少一個 LLM API key 已設定
- 建議：設定全部 3 個供應商（OpenAI、Anthropic、Gemini）

**預期輸出：**
```
🚀 Multi-Provider LLM Example

✅ OpenAI configured
✅ Anthropic configured
✅ Gemini configured

📊 Active providers: 3

============================================================
Example 1: Normal Operation (Primary Provider)
============================================================
Response: Quantum computing uses quantum mechanics...
Provider Used: OpenAILLMClient
```

**學習重點：**
- 備援鏈如何運作
- 供應商優先順序設定
- 成本最佳化技巧

---

## 🛠️ 疑難排解

### 常見問題

**1. `ModuleNotFoundError: No module named 'src'`**

**原因：** 從錯誤的目錄執行

**修復：**
```bash
# 從專案根目錄執行
cd /path/to/opencode_backend
python examples/simple_chat.py
```

**2. `Error: OPENAI_API_KEY environment variable not set`**

**原因：** 環境中缺少 API key

**修復：**
```bash
# 新增至 .env 檔案
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# 或直接 export
export OPENAI_API_KEY=sk-your-key-here
```

**3. Docker 未執行（`code_sandbox.py` 需要）**

**修復：**
```bash
# Linux
sudo systemctl start docker

# Mac / Windows
# 啟動 Docker Desktop
```

**4. 速率限制錯誤**

**原因：** 超過 LLM 供應商速率限制

**修復：**
```bash
# 設定多個供應商以自動備援
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

---

## 📖 下一步

執行範例後：

1. **閱讀文件**
   - [README.md](../README.md) — 完整概覽
   - [QUICK_START.md](../docs/QUICK_START.md) — 詳細設定指南
   - [API 文件](http://localhost:8000/docs) — 伺服器運行時可用

2. **探索程式碼**
   - `src/core/engine.py` — 主引擎邏輯
   - `src/core/processors/` — 處理器實作
   - `src/services/llm/` — LLM 整合

3. **自行建構**
   - 修改這些範例
   - 建立自訂處理器
   - 整合至你的應用程式

4. **貢獻**
   - 請參閱 [CONTRIBUTING.md](../docs/CONTRIBUTING.md)

---

## 💬 需要幫助？

- [GitHub Discussions](https://github.com/Zenobia000/openagent_backend/discussions)
- [回報問題](https://github.com/Zenobia000/openagent_backend/issues)

---

## 📄 授權

所有範例皆為 MIT 授權 — 可自由用於你的專案。
