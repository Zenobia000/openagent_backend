# 測試目錄結構

## 📁 目錄組織

```
tests/
├── unit/           # 單元測試 - 測試個別函數和類
├── integration/    # 整合測試 - 測試模組間交互
├── e2e/           # 端到端測試 - 測試完整流程
├── prompts/       # Prompts 整合測試
└── README.md      # 本文件
```

## 🧪 各類測試說明

### Unit Tests (單元測試)
- `test_engine.py` - 測試引擎核心功能
- `test_refactored_engine.py` - 測試重構後的引擎

### Integration Tests (整合測試)
- `test_api.py` - API 路由整合測試

### E2E Tests (端到端測試)
- `test_main.py` - 主程式完整流程測試
- `test_with_api.py` - API 端到端測試

### Prompts Tests (提示詞測試)
- `test_prompts_integration.py` - Prompts 整合測試
- `verify_100_percent_integration.py` - 驗證 100% prompts 整合

## 🚀 執行測試

```bash
# 執行所有測試
pytest

# 執行特定類型測試
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
pytest tests/prompts/

# 執行單個測試檔案
pytest tests/unit/test_engine.py

# 顯示詳細輸出
pytest -v

# 顯示測試覆蓋率
pytest --cov=src tests/
```

## ✅ 測試要求

1. **單元測試**：覆蓋所有核心函數
2. **整合測試**：測試服務間交互
3. **E2E 測試**：驗證完整使用案例
4. **Prompts 測試**：確保所有 prompts 正確整合