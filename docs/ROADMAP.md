# OpenCode Platform 路線圖

> **最後更新**：2026-02-24
> **目前版本**：3.2.0

OpenCode Platform 的開發願景與規劃。

---

## 🎯 願景

打造最**智慧**、**成本效益**、**生產就緒**的 AI 處理平台，具備自動複雜度路由、多供應商韌性與標準化擴展協定。

---

## ✅ 已完成

### v3.2.0（2026 年 2 月）— 持久化沙箱 + 圖表管線

- ✅ **持久化 Docker 沙箱**：透過 `attach_socket` 的 stdin/stdout JSON 通訊
- ✅ **圖表規劃管線**：每份報告最多 5 張圖表
- ✅ **CJK 字體支援**：完整的中日韓字體鏈
- ✅ **搜尋預算模型**：智慧搜尋資源分配

### v3.1.0（2026 年 2 月）— Context Engineering

- ✅ **Manus 對齊上下文工程**：6 個元件
- ✅ **Context Manager**：僅追加上下文，KV-cache 友好
- ✅ **工具可用性遮罩**：Feature Flag 控制的工具選擇
- ✅ **檔案記憶系統**：持久化代理記憶

### v3.0.0（2026 年 2 月）— 死程式碼清理 + 單體分解

- ✅ **死程式碼移除**：移除 10 個檔案（約 2,555 行）
- ✅ **DeepResearchProcessor 分解**：2,173 行 → 7 個專注模組
- ✅ **MCP/A2A 擴展**：標準化工具與代理整合
- ✅ **外掛系統**：3 個範例外掛（weather、translator、stock-analyst）
- ✅ **套件管理器**：動態載入/啟動外掛

### v2.0.0（2026 年 2 月）— Linus 風格重構

- ✅ **模組化處理器架構**：2611 行單體拆分為 12 個檔案
- ✅ **結構化例外層級**：消除字串錯誤檢測
- ✅ **多供應商 LLM**：OpenAI → Anthropic → Gemini 備援鏈
- ✅ **資料自包含**：凍結 dataclass，無字典映射
- ✅ **測試覆蓋率**：22% → 52%（+30pp）

### v1.5.0（2026 年 1 月）— 認知架構

- ✅ **雙執行時系統**：ModelRuntime + AgentRuntime
- ✅ **ComplexityAnalyzer**：自動模式路由
- ✅ **回應快取**：System 1 快取
- ✅ **Feature Flags**：YAML 驅動設定

### v1.0.0（2025 年 12 月）— 初始發布

- ✅ **FastAPI REST API**：端點 + JWT 認證
- ✅ **6 種處理模式**：chat、knowledge、search、code、thinking、research
- ✅ **SSE 串流**：即時回應串流
- ✅ **Docker 沙箱**：安全程式碼執行

---

## 🚀 Q2 2026（4 月 - 6 月）

### 效能與可擴展性

- [ ] **分散式快取** — Redis 叢集支援水平擴展
- [ ] **連線池化** — 最佳化 LLM API 連線重用
- [ ] **非同步最佳化** — 透過非同步重構降低延遲

### 可觀測性

- [ ] **OpenTelemetry 整合** — 所有 LLM 呼叫的分散式追蹤
- [ ] **Prometheus 指標** — Grafana 儀表板的詳細指標匯出
- [ ] **請求追蹤** — 跨所有元件的端到端追蹤 ID

---

## 🌟 Q3 2026（7 月 - 9 月）

### 進階 AI 功能

- [ ] **多模態支援** — 影像處理（視覺模型）、音訊處理
- [ ] **A/B 測試框架** — 內建實驗框架 + 統計分析
- [ ] **上下文視窗管理** — 大型文件自動分塊 + 智慧優先排序

### 成本管理

- [ ] **成本分析** — 每請求成本追蹤 + 供應商分解
- [ ] **預算限制** — 超過預算時自動切換至較便宜的供應商
- [ ] **使用報告** — 每日/每月成本摘要 + 最佳化建議

### 基礎設施

- [ ] **Kubernetes Operator** — CRD 自動擴展部署
- [ ] **Helm Charts** — 生產就緒 K8s 部署模板

---

## 🏢 Q4 2026（10 月 - 12 月）

### 企業功能

- [ ] **多租戶** — 隔離的使用者命名空間 + 資源配額
- [ ] **角色存取控制（RBAC）** — 細粒度權限（管理員、使用者、檢視者）
- [ ] **稽核日誌** — 合規就緒的請求日誌 + 保留政策
- [ ] **SSO 整合** — SAML/OAuth2（Azure AD、Okta）

### 整合

- [ ] **資料庫連接器** — PostgreSQL、MongoDB 原生支援
- [ ] **WebSocket 支援** — 雙向串流
- [ ] **gRPC API** — 高效能二進位協定

---

## 🔮 未來（2027+）

### 研究與創新

- **自適應路由** — ML 基礎的複雜度預測
- **自我改善提示** — 自動提示最佳化
- **邊緣部署** — IoT 與邊緣裝置

### 平台擴展

- **市集** — 社群貢獻的處理器與外掛
- **管理服務** — 完全託管的 OpenCode Cloud

---

## 🤝 貢獻路線圖

有功能需求或想貢獻？

1. **投票現有功能**：[GitHub Discussions](https://github.com/Zenobia000/openagent_backend/discussions)
2. **提出新功能**：[提交 RFC](https://github.com/Zenobia000/openagent_backend/discussions/new)
3. **實作功能**：請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)

---

**返回**：[README](../README.md) | [文件](../README.md#-文件)
