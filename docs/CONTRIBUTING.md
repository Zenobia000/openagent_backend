# 為 OpenCode Platform 做出貢獻

感謝您有興趣為 OpenCode Platform 做出貢獻！我們歡迎社群的貢獻。

## 📋 目錄

- [行為準則](#行為準則)
- [開始](#開始)
- [開發工作流程](#開發工作流程)
- [編碼標準](#編碼標準)
- [測試準則](#測試準則)
- [Pull Request 流程](#pull-request-流程)
- [社群](#社群)

---

## 行為準則

### 我們的標準

- **尊重**：以尊重和體貼對待每個人
- **合作**：建設性地合作
- **專業**：專注於技術價值，而非人身攻擊
- **包容**：歡迎來自所有背景的貢獻者

---

## 開始

### 前置需求

- **Python** 3.11 或更高版本
- **uv**（推薦的套件管理器）
- **Git**
- **Docker**（選用，用於測試沙箱功能）

### Fork 並 Clone

```bash
# 在 GitHub 上 Fork 專案
# 然後 clone 你的 fork
git clone https://github.com/YOUR_USERNAME/openagent_backend.git
cd openagent_backend

# 新增 upstream remote
git remote add upstream https://github.com/Zenobia000/openagent_backend.git
```

### 開發環境設定

```bash
# 安裝 uv（如尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 建立虛擬環境
uv venv --python 3.11
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安裝相依套件（含開發工具）
uv pip install -e ".[dev]"

# 複製環境變數範本
cp .env.example .env
# 編輯 .env 並新增你的 API key
```

### 驗證安裝

```bash
# 執行測試
uv run pytest tests/ -v -o "addopts="

# 啟動 CLI
python main.py

# 啟動 API 伺服器
cd src && python -c "
import uvicorn
from api.routes import create_app
uvicorn.run(create_app(), host='0.0.0.0', port=8000)
"
```

---

## 開發工作流程

### 1. 建立 Feature Branch

```bash
# 更新你的 fork
git fetch upstream
git checkout main
git merge upstream/main

# 建立 feature branch
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/bug-description
```

### Branch 命名慣例

- `feature/` — 新功能
- `fix/` — Bug 修復
- `docs/` — 文件更新
- `refactor/` — 程式碼重構
- `test/` — 測試新增或修復
- `chore/` — 維護任務

### 2. 提交變更

我們使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```bash
git commit -m "feat(processors): 新增自訂處理器註冊 API"
git commit -m "fix(llm): 修復多供應商備援中的逾時"
git commit -m "docs(readme): 新增效能基準章節"
```

**提交類型**：
- `feat`：新功能
- `fix`：Bug 修復
- `docs`：僅文件
- `style`：程式碼風格（格式化，無邏輯變更）
- `refactor`：程式碼重構
- `test`：新增或更新測試
- `chore`：維護任務

---

## 編碼標準

### Linus Torvalds 哲學

我們遵循 Linus Torvalds 的原則，撰寫乾淨、可維護的程式碼：

**1. 好品味 — 消除特例**
```python
# ❌ 不好 — 特例
if mode == "chat":
    level = "system1"
elif mode == "search":
    level = "system2"

# ✅ 好 — 資料自包含
@dataclass(frozen=True)
class ProcessingMode:
    name: str
    cognitive_level: str

mode = ProcessingMode("chat", "system1")
level = mode.cognitive_level  # 無特例
```

**2. 簡潔 — 函數 ≤50 行**
```python
# ❌ 不好 — 200 行怪獸函數
def process_everything(request):
    # ... 200 行混合關注點

# ✅ 好 — 小而專注的函數
def process(request):
    validated = validate_request(request)
    mode = select_mode(validated)
    result = execute_processor(mode, validated)
    return format_response(result)
```

**3. 無深層巢狀 — 縮排 ≤3 層**
```python
# ✅ 好 — 提前返回，扁平結構
def good_function():
    if not condition1:
        return
    if not condition2:
        return
    for item in items:
        if not item.valid:
            continue
        item.process()
```

### Python 風格指南

- **PEP 8 合規**：使用 `black` 格式化
- **行長度**：最多 100 字元
- **型別提示**：所有函數必須有型別註解
- **Docstrings**：使用 Google 風格

### 檔案組織

- **檔案 ≤500 行**：超過則拆分為多個檔案
- **單一職責**：每個檔案一個類別/概念
- **一致的命名**：
  - 檔案：`snake_case.py`
  - 類別：`PascalCase`
  - 函數/變數：`snake_case`
  - 常數：`UPPER_SNAKE_CASE`

---

## 測試準則

### 測試覆蓋率要求

- **新功能**：≥80% 覆蓋率
- **Bug 修復**：新增迴歸測試
- **重構**：維持現有覆蓋率

### 執行測試

```bash
# 執行所有測試
uv run pytest tests/ -v -o "addopts="

# 執行特定測試檔案
uv run pytest tests/unit/test_models_v2.py -v -o "addopts="

# 含覆蓋率
uv run pytest tests/ --cov=src --cov-report=html -o "addopts="

# 僅快速測試（跳過整合）
uv run pytest tests/unit/ -v -o "addopts="
```

### 測試命名慣例

```python
# 模式：test_<什麼>_<條件>_<預期>
def test_router_simple_query_selects_system1():
    pass

def test_processor_invalid_input_raises_validation_error():
    pass
```

---

## Pull Request 流程

### 提交前

- [ ] 所有測試通過（`uv run pytest tests/ -v -o "addopts="`）
- [ ] 新程式碼覆蓋率 ≥80%
- [ ] 使用 `black` 格式化（`black src/ tests/`）
- [ ] 型別檢查通過（`mypy src/`）
- [ ] 無 linting 錯誤
- [ ] 文件已更新（如需要）
- [ ] CHANGELOG.md 已更新（如使用者可見的變更）

### PR 標題格式

使用 Conventional Commits 格式：
```
feat(processors): 新增自訂處理器註冊 API
fix(llm): 修復多供應商備援中的逾時
```

### 審查流程

1. **自動檢查**：CI/CD 管線執行測試、linting、型別檢查
2. **程式碼審查**：維護者審查程式碼（通常 1-3 個工作天）
3. **回饋**：透過推送新提交回應審查意見
4. **核准**：核准後由維護者合併

---

## 貢獻者專案結構

```
opencode_backend/
├── src/
│   ├── core/                 # 核心引擎邏輯
│   │   ├── engine.py         # 主引擎
│   │   ├── router.py         # 請求路由
│   │   ├── models_v2.py      # 資料模型（在此新增模式）
│   │   ├── processors/       # 在此新增自訂處理器
│   │   │   ├── base.py       # 繼承此類別建立新處理器
│   │   │   └── factory.py    # 在此註冊處理器
│   │   ├── context/          # Context Engineering 元件
│   │   └── runtime/          # 執行時實作
│   ├── services/             # 外部服務
│   │   ├── llm/              # 在此新增 LLM 供應商
│   │   ├── knowledge/        # RAG 實作
│   │   ├── search/           # 搜尋整合
│   │   └── sandbox/          # 沙箱服務
│   └── api/                  # REST API
│       └── routes.py         # 在此新增端點
├── packages/                 # 在此新增 MCP/A2A 外掛
├── tests/
│   ├── unit/                 # 在此新增單元測試
│   ├── integration/          # 在此新增整合測試
│   └── e2e/                  # 在此新增端到端測試
└── docs/                     # 文件
```

---

## 社群

### 溝通管道

- **GitHub Discussions**：[問題與想法](https://github.com/Zenobia000/openagent_backend/discussions)
- **GitHub Issues**：[Bug 回報與功能請求](https://github.com/Zenobia000/openagent_backend/issues)

### 取得幫助

- 閱讀 [README.md](../README.md) 和文件
- 搜尋[現有 issues](https://github.com/Zenobia000/openagent_backend/issues)
- 在 [GitHub Discussions](https://github.com/Zenobia000/openagent_backend/discussions) 中提問

---

感謝您為 OpenCode Platform 做出貢獻！
