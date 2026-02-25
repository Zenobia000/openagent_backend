# 常見問題（FAQ）

> **最後更新**：2026-02-24
> **快速連結**：[一般](#一般問題) | [技術](#技術問題) | [效能](#效能問題) | [安全](#安全問題) | [貢獻](#貢獻問題)

OpenCode Platform 常見問題。

---

## 一般問題

### 為什麼需要另一個 AI 框架？LangChain/Haystack 不夠嗎？

**簡短回答**：OpenCode 專注於**認知路由**與**生產就緒性**，而非僅僅 LLM 串接。

**主要差異化**：
- ✅ **自動複雜度路由** — 不是所有任務都需要昂貴的自主代理
- ✅ **內建多供應商備援** — 開箱即用
- ✅ **生產 API** — 認證、串流、Feature Flags 內建
- ✅ **MCP/A2A 擴展** — 標準化的工具與代理整合協定
- ✅ **成本最佳化** — 透過智慧快取節省成本

**何時使用替代方案**：請參閱 [比較指南](COMPARISON.md)

---

### 可以不用 Docker 嗎？

**可以！** Docker 是**選用的**。

**需要 Docker 的功能**：
- ✅ 程式碼沙箱執行（`/api/v1/sandbox/execute`）
- ✅ Qdrant 向量資料庫（知識服務）

**不需要 Docker 的功能**：
- ✅ 聊天、思考、搜尋模式
- ✅ API 伺服器
- ✅ CLI 介面
- ✅ 多供應商 LLM

**最低需求**：Python 3.11+

---

### 支援哪些 LLM 供應商？

**目前支援**：
- ✅ **OpenAI** — GPT-4o、GPT-4o-mini
- ✅ **Anthropic** — Claude 4 Opus、Claude 4 Sonnet、Claude 3.5 Haiku
- ✅ **Google Gemini** — Gemini Pro

**運作方式**：自動備援鏈（OpenAI → Anthropic → Gemini）

---

### 已經準備好上線了嗎？

**是的。** 證據如下：

| 指標 | 值 | 狀態 |
|------|----|----|
| **Feature Flags** | YAML 驅動 | 零風險部署 ✅ |
| **程式碼品質** | 9/10（Linus 風格） | ✅ |
| **例外處理** | 結構化層級 | ✅ |
| **擴展性** | MCP/A2A 協定 | ✅ |

**建議**：從 Feature Flags 全部關閉開始，逐步啟用

---

### 授權是什麼？

**MIT License** — 可商業使用。

**你可以**：
- ✅ 商業使用
- ✅ 修改程式碼
- ✅ 發行
- ✅ 再授權
- ✅ 用於閉源產品

**你必須**：
- ✅ 包含授權聲明

詳見 [LICENSE](../LICENSE)。

---

## 技術問題

### Router 如何分類請求複雜度？

`ComplexityAnalyzer` 使用多種啟發式方法：

```python
def analyze_complexity(self, query: str) -> float:
    score = 0.0

    # 1. 查詢長度（越長 = 越複雜）
    if len(query) > 200:
        score += 0.3

    # 2. 關鍵字偵測
    analytical_keywords = ["analyze", "compare", "research", "evaluate"]
    if any(kw in query.lower() for kw in analytical_keywords):
        score += 0.4

    # 3. 問題深度（多部分問題）
    question_count = query.count("?")
    score += min(question_count * 0.2, 0.3)

    return min(score, 1.0)
```

**閾值**：
- `< 0.3` → System 1（chat/knowledge）
- `0.3 - 0.7` → System 2（search/code/thinking）
- `> 0.7` → Agent（deep_research）

**覆寫**：使用明確的 `mode` 參數繞過路由

---

### 可以新增自訂處理器嗎？

**可以！** 繼承 `BaseProcessor` 並註冊：

```python
from src.core.processors.base import BaseProcessor
from src.core.models_v2 import Modes

# 1. 建立自訂處理器
class TranslationProcessor(BaseProcessor):
    def process(self, request):
        translated = self.llm_client.generate(
            prompt=f"翻譯至 {request.context['target_lang']}: {request.query}"
        )
        return Response(content=translated)

# 2. 在 factory 中註冊
# 3. 使用它
result = engine.process(Request(
    query="Hello, world!",
    mode="translation",
    context={"target_lang": "Spanish"}
))
```

---

### 多供應商備援如何運作？

**自動重試鏈**與指數退避：

```python
providers = [
    OpenAIClient(),      # 主要
    AnthropicClient(),   # 備援 1
    GeminiClient()       # 備援 2
]

for provider in providers:
    try:
        return provider.generate(prompt)
    except ProviderError as e:
        if e.retryable and provider != providers[-1]:
            continue  # 嘗試下一個供應商
        else:
            raise
```

**觸發備援**：
- ✅ 速率限制錯誤（HTTP 429）
- ✅ 服務不可用（HTTP 503）
- ✅ 逾時錯誤

**不觸發備援**（立即失敗）：
- ❌ 無效 API key（HTTP 401）
- ❌ 無效請求（HTTP 400）
- ❌ 內容政策違規

---

### System 1 和 System 2 有什麼差別？

基於認知心理學的[雙歷程理論](https://en.wikipedia.org/wiki/Dual_process_theory)：

| 面向 | System 1 | System 2 |
|------|----------|----------|
| **速度** | 快速 | 較慢（0.8-2.3s 平均） |
| **快取** | 是 | 否 |
| **用途** | 聊天、知識檢索 | 分析、程式碼、搜尋 |
| **複雜度** | 低 | 中-高 |

**System 1**：自動、直覺、快速
**System 2**：分析、審慎、較慢
**Agent**：多步驟、自主工作流程

---

## 效能問題

### 可以處理 1000 req/s 嗎？

**適當設定下：可以**

| 設定 | 吞吐量 | 備註 |
|------|--------|------|
| **單一實例** | ~100 req/s | 受 LLM API 限制 |
| **單一實例 + 快取** | ~450 req/s | 僅 System 1 |
| **5 實例 + 快取** | ~2000 req/s | Kubernetes HPA |

**瓶頸**：LLM API 速率限制，而非平台本身

**詳見**：[效能基準](PERFORMANCE.md)

---

### 運行成本多少？

**取決於 LLM 使用量**。範例：每天 1000 請求

**無快取**：
```
1000 請求 × $0.01/請求 = $10/天 = $300/月
```

**啟用 System 1 快取**：
```
LLM 請求大幅減少，依快取命中率而定
```

---

### 有託管/管理版本嗎？

**尚未提供。**

**目前選項**：
- ✅ 透過 Docker/Kubernetes 自行部署

---

## 安全問題

### API key 如何儲存？

**絕不存在程式碼或日誌中**。只在：

1. **開發**：`.env` 檔案（絕不提交至 git）
2. **生產**：Kubernetes secrets
3. **環境變數**：執行時載入

**安全功能**：
- ✅ 所有日誌中已遮蔽
- ✅ 不包含在錯誤訊息中
- ✅ 不傳送至客戶端回應

---

### 程式碼執行安全嗎？

**是的**，透過 Docker 沙箱隔離：

- ✅ **隔離容器** — 無法存取主機系統
- ✅ **無網路存取** — 無法連接外部服務
- ✅ **資源限制** — CPU、記憶體、時間約束
- ✅ **唯讀檔案系統** — 除 `/tmp` 目錄外
- ✅ **非 root 使用者** — 以非特權使用者執行
- ✅ **自動清理** — 執行後容器銷毀

**詳見**：[SECURITY.md](SECURITY.md)

---

### 如何回報安全漏洞？

**請勿**開啟公開 GitHub issue

**請改為**：
1. 寄送 Email 至 **security@opencode.ai**
2. 包含：漏洞描述、重現步驟、潛在影響

**回應時間**：
- 確認：**48 小時**內
- 初步評估：**5 個工作天**內

---

## 貢獻問題

### 如何貢獻？

**歡迎貢獻！** 請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)

**我們需要幫助的領域**：
1. **文件** — 教學、範例、翻譯
2. **測試** — 測試覆蓋率（目標：80%）
3. **Bug 修復** — 請參閱 [good first issue](https://github.com/Zenobia000/openagent_backend/labels/good%20first%20issue)
4. **新功能** — 請參閱 [路線圖](ROADMAP.md)

**快速開始**：
```bash
# Fork 並 clone
git clone https://github.com/YOUR_USERNAME/openagent_backend.git

# 設定開發環境
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[dev]"

# 執行測試
uv run pytest tests/
```

---

### 程式碼審查流程是什麼？

1. **Fork** 並建立 feature branch
2. **修改** 並撰寫測試（≥80% 覆蓋率）
3. **提交 PR** 附上清楚說明
4. **自動檢查** — 測試、linting、型別檢查
5. **程式碼審查** — 維護者審查（1-3 天）
6. **合併**

---

### 可以商業使用嗎？

**可以！** MIT License 允許商業使用。

**無限制**：
- ✅ 商業產品
- ✅ 閉源應用程式
- ✅ 基於 OpenCode 販售服務

**唯一要求**：包含授權聲明

---

## 還有問題嗎？

- [GitHub Discussions](https://github.com/Zenobia000/openagent_backend/discussions) — 問題與想法
- [GitHub Issues](https://github.com/Zenobia000/openagent_backend/issues) — Bug 回報

---

**返回**：[README](../README.md) | [文件](../README.md#-文件)
