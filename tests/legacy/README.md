# Legacy Tests Archive

此目錄包含舊版測試腳本，這些腳本不是標準的 pytest 測試。

## 遷移原因

這些文件被移到這裡因為：
1. **不是 pytest 測試** - 使用 `if __name__ == "__main__"` 的獨立腳本
2. **測試陳舊功能** - 測試已重構或移除的代碼
3. **不符合測試標準** - 沒有使用 pytest fixtures 或標準測試結構

## 文件列表

- `simple_test.py` - 批判性分析檢測邏輯測試腳本
- `test_code_fix.py` - 代碼修復處理器測試腳本
- `test_critical_analysis_integration.py` - 批判性分析集成測試腳本
- `test_deep_research.py` - 深度研究處理器測試腳本
- `test_enhanced_citation_stats.py` - 引用統計增強測試
- `test_enhanced_research.py` - 研究功能增強測試
- `test_llm.py` - LLM 基礎測試腳本
- `test_reference_categorization.py` - 參考文獻分類測試

## 如何使用這些腳本

這些是獨立的 Python 腳本，不是pytest測試。要運行它們：

```bash
python tests/legacy/simple_test.py
python tests/legacy/test_llm.py
# ... 等等
```

## 遷移到標準測試

如果需要將這些轉換為標準測試：
1. 移除 `if __name__ == "__main__"`
2. 將主函數拆分為多個 `def test_*()` 函數
3. 使用 pytest fixtures 進行設置
4. 添加適當的 assertions
5. 移回 `tests/unit/` 或 `tests/integration/`

---

**創建日期**: 2026-02-14
**重構階段**: Phase 0 - 測試清理
