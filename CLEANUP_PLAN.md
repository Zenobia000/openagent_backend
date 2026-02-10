# OpenCode Platform - 資料夾清理計畫

## 現有結構分析

### 🔴 需要移除的檔案/資料夾

1. **重複的核心引擎**
   - `src/core/unified_final_engine.py` - 被 refactored 版本取代
   - `src/core/enhanced_engine.py` - 示例代碼，不需要
   - `src/core/opencode_engine.py` - 舊版本

2. **重複的日誌系統**
   - `src/utils/logger.py` - 舊版
   - `src/utils/unified_logger.py` - 被 refactored/logger.py 取代
   - `src/utils/logging_config.py` - 舊版

3. **未使用的服務**
   - `src/services/mcp/` - MCP 協議未實現
   - `src/services/collections/` - 未使用
   - `src/services/data_services/` - 空資料夾
   - `src/services/deep_research/` - 未整合

4. **過時的 opencode 命名空間**
   - 所有使用 `from opencode.` 的導入都失敗
   - 需要統一改為相對導入

5. **__pycache__ 資料夾**
   - 所有 __pycache__ 需要清理

### 🟡 需要重構的檔案

1. **服務層**
   - `src/services/knowledge/` - 導入路徑問題
   - `src/services/search/` - 導入路徑問題
   - `src/services/sandbox/` - 導入路徑問題

2. **API 路由**
   - `src/api/routes.py` - 需要更新到新引擎

### 🟢 保留並整理的檔案

1. **核心系統 (重構版)**
   ```
   src/core/refactored/
   ├── __init__.py
   ├── models.py
   ├── logger.py
   ├── processor.py
   └── engine.py
   ```

2. **基礎服務**
   ```
   src/services/
   ├── llm/
   │   └── openai_client.py
   ├── knowledge/
   │   └── (修復後保留)
   └── search/
       └── (修復後保留)
   ```

3. **工具類**
   ```
   src/utils/
   └── helpers.py (如果有用)
   ```

4. **認證系統**
   ```
   src/auth/
   └── (如果需要保留)
   ```

## 建議的新結構

```
src/
├── core/               # 核心引擎 (使用 refactored 版本)
│   ├── __init__.py
│   ├── engine.py
│   ├── processor.py
│   ├── models.py
│   └── logger.py
├── services/           # 服務層
│   ├── __init__.py
│   ├── llm.py        # LLM 客戶端
│   ├── knowledge.py   # 知識庫服務
│   ├── search.py      # 搜索服務
│   └── sandbox.py     # 代碼執行服務
├── api/               # API 層
│   ├── __init__.py
│   ├── app.py        # FastAPI 應用
│   └── routes.py     # 路由定義
├── config.py          # 配置文件
└── main.py           # 主入口

```

## 清理步驟

### Step 1: 備份重要檔案
```bash
# 創建備份
mkdir -p backup/src_old
cp -r src/* backup/src_old/
```

### Step 2: 移除 __pycache__
```bash
find src -type d -name __pycache__ -exec rm -rf {} +
```

### Step 3: 移除過時檔案
```bash
# 移除舊引擎
rm src/core/unified_final_engine.py
rm src/core/enhanced_engine.py
rm src/core/opencode_engine.py

# 移除舊日誌系統
rm src/utils/logger.py
rm src/utils/unified_logger.py
rm src/utils/logging_config.py

# 移除未使用的服務
rm -rf src/services/mcp/
rm -rf src/services/collections/
rm -rf src/services/data_services/
rm -rf src/services/deep_research/
```

### Step 4: 重組資料夾
```bash
# 將 refactored 提升為主要 core
mv src/core/refactored/* src/core/
rm -rf src/core/refactored

# 簡化服務結構
# (需要手動整理各服務為單一檔案)
```

### Step 5: 修復導入
- 移除所有 `from opencode.` 導入
- 統一使用相對導入或絕對導入（從 src 開始）

### Step 6: 更新配置
- 更新 config.py
- 確保 .env 配置正確

## 預期結果

- **減少 60% 的代碼量**
- **清晰的模組邊界**
- **統一的導入路徑**
- **移除所有重複代碼**
- **簡化的資料夾結構**