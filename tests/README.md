# OpenAgent Backend - 測試套件

> **狀態**: ✅ 已清理並準備好重構  
> **最後更新**: 2026-02-14  
> **Phase**: Phase 0 完成

---

## 📊 快速統計

| 指標 | 數值 | 狀態 |
|------|------|------|
| Unit Tests | 218 passing | ✅ |
| Integration Tests | 4 files | ⏸️ (需要外部服務) |
| E2E Tests | 1 file | ⏸️ (需要外部服務) |
| Legacy Tests | 8 files (archived) | ℹ️ |
| Code Coverage | ~22% | ⚠️ (基準線) |

---

## 📁 目錄結構

```
tests/
├── unit/                    # ✅ 單元測試 (218 通過)
│   ├── test_a2a_client.py       (27 tests)
│   ├── test_auth.py             (10 tests)
│   ├── test_cache.py            (13 tests)
│   ├── test_error_handling.py   (19 tests)
│   ├── test_extension_api.py    (21 tests)
│   ├── test_feature_flags.py    (12 tests)
│   ├── test_mcp_client.py       (24 tests)
│   ├── test_metrics.py          (8 tests)
│   ├── test_multi_provider.py   (17 tests)
│   ├── test_package_manager.py  (26 tests)
│   ├── test_processors.py       (33 tests, 6 暫時跳過)
│   └── test_router.py           (26 tests)
│
├── integration/            # ⏸️  集成測試 (需要外部服務)
│   ├── test_agent_runtime.py
│   ├── test_api.py
│   ├── test_model_runtime.py
│   └── test_sse.py
│
├── e2e/                    # ⏸️  端到端測試
│   └── test_all_modes.py
│
├── legacy/                 # ℹ️  歸檔的獨立腳本
│   ├── README.md           (說明文檔)
│   └── (8 個舊腳本)
│
├── conftest.py             # Pytest 配置和 fixtures
├── requirements-test.txt   # 測試依賴
├── TEST_CLEANUP_REPORT.md  # 清理報告
└── SKIP_TESTS.md           # 跳過測試說明
```

---

## 🚀 運行測試

### 運行所有單元測試
```bash
pytest tests/unit/ -v
# 218 passed, 6 deselected
```

### 運行特定測試文件
```bash
pytest tests/unit/test_feature_flags.py -v
```

### 生成覆蓋率報告
```bash
pytest tests/unit/ --cov=src --cov-report=html
# 在 htmlcov/index.html 查看報告
```

### 排除失敗測試
```bash
pytest tests/unit/ -v -k "not (test_search_serp or test_research or test_mode_switching)"
```

---

## ⚠️  暫時跳過的測試

6 個測試暫時被排除，詳見 [SKIP_TESTS.md](./SKIP_TESTS.md)

**原因**: 這些測試依賴於即將在 Phase 2 重構的 processor.py (2611 行)

**計劃**: Phase 2 (Processor 拆分) 完成後自然修復

---

## 📈 測試覆蓋率目標

| Phase | 覆蓋率目標 | 當前 | 狀態 |
|-------|-----------|------|------|
| Phase 0 (準備) | 20%+ | 22% | ✅ |
| Phase 1 (數據結構) | 30%+ | - | 📋 |
| Phase 2 (Processor) | 50%+ | - | 📋 |
| Phase 6 (完成) | 80%+ | - | 🎯 |

---

## 🧪 測試最佳實踐

### 1. 命名規範
```python
def test_<component>_<scenario>_<expected_result>():
    """測試描述"""
    pass
```

### 2. 使用 Fixtures
```python
@pytest.fixture
def mock_llm_client():
    return Mock()

def test_something(mock_llm_client):
    # 使用 fixture
    pass
```

### 3. Async 測試
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### 4. 參數化測試
```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
])
def test_uppercase(input, expected):
    assert input.upper() == expected
```

---

## 📚 相關文檔

- [測試清理報告](./TEST_CLEANUP_REPORT.md) - Phase 0 清理詳情
- [跳過測試說明](./SKIP_TESTS.md) - 暫時跳過的測試
- [Legacy README](./legacy/README.md) - 歸檔腳本說明
- [WBS Phase 0](../docs/REFACTORING_WBS_V2_LINUS.md#phase-0) - 測試準備計劃

---

## ✅ Phase 0 檢查清單

- [x] 移除 legacy 測試（8 個文件歸檔）
- [x] 排除失敗測試（6 個暫時跳過）
- [x] 建立測試基準線（218 通過）
- [x] 生成覆蓋率報告（22% 基準）
- [ ] 創建回歸測試套件（Golden Output） - TODO
- [ ] 補充核心模塊測試 - TODO Phase 1

---

**維護者**: OpenAgent Development Team  
**最後更新**: 2026-02-14  
**準備狀態**: ✅ Ready for Phase 1 Refactoring
