# 實施規劃文件索引

## 文檔總覽

本目錄包含基於 OpenAgent v3.0 架構的 **Context Engineering 實施規劃**。

**重要**：本文件集已根據 [Manus Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents) 的生產經驗進行修訂（V2）。原始基於神經科學理論的認知組件設計已被 KV-Cache 友好的 Context 管理方案取代。

---

## 核心規劃文件（必讀）

### 1. [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) (V2)
**深度架構差距分析 + Manus 矛盾分析**

**適合對象**：架構師、技術決策者
**閱讀時間**：45 分鐘
**關鍵內容**：
- 6 大矛盾分析（原始設計 vs Manus 生產經驗）
- 三方架構比較（v3.0 vs 原始認知架構 vs Manus Context Engineering）
- 修訂優先級矩陣
- Linus 風格 + Manus 檢查清單

**核心發現**：
```
CRITICAL: GlobalWorkspace 破壞 KV-Cache → 改用 AppendOnlyContext
CRITICAL: OODA Router 切換破壞快取 → 改用 Logit Masking
SEVERE:   MetacogGovernor 過度設計 → 改用 todo.md 覆誦
```

---

### 2. [IMPLEMENTATION_PLAN_V2.md](./IMPLEMENTATION_PLAN_V2.md) (V3)
**4 週實施計劃（Context Engineering）**

**適合對象**：後端工程師、測試工程師
**閱讀時間**：60 分鐘
**關鍵內容**：
- 6 個 Context Engineering 工具的完整代碼示例
- Engine 整合方式
- 完整測試計劃（單元 + 整合 + 性能）

**階段劃分**：
```
Phase 0 (3 天): 準備 & KV-Cache 基線測量
Phase 1 (1.5 週): ContextManager + TodoRecitation + ErrorPreservation
Phase 2 (1.5 週): ToolMask + TemplateRandomizer + FileBasedMemory
Phase 3 (2 天): 端到端測試 & 驗證
```

---

### 3. [WBS_DETAILED.md](./WBS_DETAILED.md) (V2)
**詳細工作分解結構**

**適合對象**：專案經理、執行團隊
**閱讀時間**：30 分鐘
**關鍵內容**：
- 16 個可執行任務（TASK-001 to TASK-016）
- 每個任務的估算時間（人天）
- 依賴關係圖
- 15 人天總投入

**任務結構**：
```
0.0 Context Engineering 實施（4 週，15 人天）
+-- 1.0 Phase 0: 準備（3 人天，3 個任務）
+-- 2.0 Phase 1: Context 核心（6 人天，6 個任務）
+-- 3.0 Phase 2: 工具約束（4 人天，5 個任務）
+-- 4.0 Phase 3: 驗證（2 人天，2 個任務）
```

---

## Manus Context Engineering 六大原則

| # | 原則 | 對應組件 | 代碼量 |
|---|------|---------|-------|
| 1 | **KV-Cache 命中率** — append-only context | ContextManager | ~100 行 |
| 2 | **Mask, Don't Remove** — logit masking | ToolAvailabilityMask | ~60 行 |
| 3 | **File System as Context** — 檔案系統記憶 | FileBasedMemory | ~50 行 |
| 4 | **Attention via Recitation** — todo.md 覆誦 | TodoRecitation | ~60 行 |
| 5 | **Keep Erroneous Turns** — 錯誤保留 | ErrorPreservation | ~40 行 |
| 6 | **Avoid Few-Shot Traps** — 結構性雜訊 | TemplateRandomizer | ~40 行 |

**總計**: ~350 行生產代碼

---

## 原始設計文件（理論參考）

以下是原始的類人類思維架構設計文檔。**注意**：這些文件的部分設計已被 Manus 經驗推翻。

| 文檔 | 描述 | 狀態 | 備註 |
|-----|------|------|------|
| [00_overview_and_vision.md](./00_overview_and_vision.md) | 總覽與願景 | 理論參考 | 6 層架構過度設計 |
| [01_global_workspace_design.md](./01_global_workspace_design.md) | 全域工作空間設計 | **已廢止** | 破壞 KV-Cache |
| [02_metacognitive_governor.md](./02_metacognitive_governor.md) | 元認知治理設計 | **已廢止** | todo.md 更簡單 |
| [03_ooda_loop_router.md](./03_ooda_loop_router.md) | OODA 路由設計 | **已廢止** | Logit mask 更安全 |
| [08_implementation_roadmap.md](./08_implementation_roadmap.md) | 原始 16 週計劃 | **已廢止** | 4 週 Context Engineering |
| [09_migration_strategy.md](./09_migration_strategy.md) | 原始遷移策略 | 部分參考 | Feature Flag 部分仍有效 |

---

## 快速開始指南

### 如果你是...

#### 1. **技術決策者（架構師、CTO）**
**目標**：決定是否實施 Context Engineering

**閱讀路徑**：
1. [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) - 修訂說明 + 執行摘要（10 分鐘）
2. [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) - 第 2 節：6 大矛盾分析（20 分鐘）
3. [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) - 第 7 節：結論（5 分鐘）

**決策點**：
- 投入：15 人天，<500 行代碼
- 收益：KV-Cache 命中率 >80%，Token 成本 -20~30%
- 風險：極低（Feature Flag 即時回滾）

---

#### 2. **後端工程師（實施者）**
**目標**：開始實施

**閱讀路徑**：
1. [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) - 第 1.3 節：修訂目標架構（10 分鐘）
2. [IMPLEMENTATION_PLAN_V2.md](./IMPLEMENTATION_PLAN_V2.md) - 第 3 節：Phase 1 代碼示例（30 分鐘）
3. [WBS_DETAILED.md](./WBS_DETAILED.md) - TASK-004 到 TASK-009（20 分鐘）

**開始實施**：
```bash
# 1. 建立 Feature Branch
git checkout -b feature/context-engineering-phase1

# 2. 執行 TASK-001: Feature Flag 配置
# 參考：WBS_DETAILED.md - 任務 1.1

# 3. 執行 TASK-004: ContextEntry 數據模型
# 參考：IMPLEMENTATION_PLAN_V2.md - 第 3.2.1 節
```

---

#### 3. **專案經理（PM）**
**目標**：規劃與追蹤

**閱讀路徑**：
1. [WBS_DETAILED.md](./WBS_DETAILED.md) - WBS 層次結構（5 分鐘）
2. [WBS_DETAILED.md](./WBS_DETAILED.md) - 附錄 B：資源需求（5 分鐘）
3. [WBS_DETAILED.md](./WBS_DETAILED.md) - 附錄 D：驗收檢查清單（5 分鐘）

**專案追蹤**：
```
Sprint 1 (Day 1-3): TASK-001 to TASK-003 (Phase 0)
Sprint 2 (Week 1-2): TASK-004 to TASK-009 (Phase 1)
Sprint 3 (Week 2.5-3.5): TASK-010 to TASK-014 (Phase 2)
Sprint 4 (Week 4): TASK-015 to TASK-016 (Phase 3)
```

---

## 文檔對比表

| 項目 | 原始文檔 | V1 規劃 | V2 規劃 (Manus) |
|------|---------|---------|-----------------|
| **實施時長** | 16 週 | 6 週 | **4 週** |
| **代碼量** | >10,000 行 | <2,000 行 | **<500 行** |
| **組件數** | 6 個 | 3 個 | **0 個** (工具類) |
| **投入（人天）** | ~80 | ~35 | **~15** |
| **KV-Cache** | 未考慮 | 破壞 | **保護** |
| **風險** | 高 | 低 | **極低** |

**關鍵演進**：
- 原始：神經科學理論驅動（Big Bang 16 週）
- V1：Linus 極簡主義（漸進式 6 週）
- **V2：Manus 生產經驗（Context Engineering 4 週）**

---

## 成功標準

### Phase 0 成功標準
- [ ] KV-Cache 基線已測量
- [ ] 品質基線已建立
- [ ] 測試框架準備完成

### Phase 1 成功標準
- [ ] KV-Cache 命中率 >80%
- [ ] 品質 >= 基線
- [ ] 性能開銷 <50ms

### Phase 2 成功標準
- [ ] KV-Cache 命中率 >90%
- [ ] 模板多樣性 > 1
- [ ] 工具選擇正確率 >= 基線

### 最終成功標準
- [ ] 所有 Phase 驗收通過
- [ ] Token 成本降低 >20%
- [ ] 文檔更新完成

---

## 支援與回饋

### 問題回報
- 技術問題：開啟 GitHub Issue
- 架構討論：每週三架構評審會議

### 文檔維護
- 維護者：OpenAgent Architecture Team
- 更新頻率：每週 Sprint Review
- 最後更新：2026-02-14

---

## 授權

本文檔集與相關代碼遵循 [MIT License](../../LICENSE)

---

**下一步**：
1. 閱讀 [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) 了解 6 大矛盾
2. 閱讀 [IMPLEMENTATION_PLAN_V2.md](./IMPLEMENTATION_PLAN_V2.md) 了解代碼示例
3. 閱讀 [WBS_DETAILED.md](./WBS_DETAILED.md) 開始執行任務

**立即開始**：
```bash
git checkout -b feature/context-engineering-phase0
# 開始 Phase 0
# 參考：IMPLEMENTATION_PLAN_V2.md - 第 2 節
```
