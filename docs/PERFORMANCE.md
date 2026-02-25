# 效能基準

> **最後更新**：2026-02-24
> **版本**：3.2.0

OpenCode Platform 各認知層級的效能指標。

---

## 📊 各認知層級延遲

### 摘要表

| 模式 | 層級 | 平均延遲 | P95 延遲 | Token/請求 |
|------|------|---------|---------|-----------|
| **chat** | System 1 | 45ms | 120ms | ~150 |
| **knowledge** | System 1 | 89ms | 210ms | ~300 |
| **search** | System 2 | 1.2s | 2.5s | ~800 |
| **code** | System 2 | 850ms | 1.8s | ~600 |
| **thinking** | System 2 | 2.3s | 4.1s | ~1200 |
| **deep_research** | Agent | 8.5s | 15s | ~3000 |

### 測試環境

- **LLM 供應商**：OpenAI GPT-4o
- **硬體**：4 vCPU、8GB RAM
- **負載**：10 個並行請求/秒
- **快取**：Redis（僅 System 1）

**注意**：以上數據為特定測試環境下的參考值，實際效能因網路、供應商負載等因素而異。

---

## 🚀 可擴展性指標

### 吞吐量

| 指標 | 值 | 備註 |
|------|----|----|
| **最大並行請求** | 100 req/s | 單一實例，無快取 |
| **啟用快取（System 1）** | ~450 req/s | 高快取命中率 |
| **備援延遲開銷** | <100ms | OpenAI → Anthropic 切換 |
| **記憶體使用** | ~800MB | 基本 + 處理器 |

### 水平擴展

| 實例數 | 最大吞吐量 | 備註 |
|--------|-----------|------|
| 1 | 100 req/s | 基線 |
| 3 | 280 req/s | +180%（線性擴展） |
| 5 | 450 req/s | +350%（接近線性） |
| 10 | 850 req/s | +750%（略有退化） |

**瓶頸**：LLM API 速率限制（非平台本身）

---

## 💰 成本最佳化

### 快取影響

System 1 快取可大幅減少重複查詢的 LLM 成本：

```
無快取：1000 請求 × $0.01 = $10.00
啟用快取：視快取命中率而定，可節省 50-80%
```

### 月成本估算

**情境：小型團隊（10,000 請求/月）**

| 設定 | LLM 呼叫 | 成本 |
|------|---------|------|
| 無快取 | 10,000 | $100 |
| System 1 快取 | 大幅減少 | 依命中率 |
| + 多供應商 | 進一步降低 | 使用較便宜的備援供應商 |

---

## 🔥 供應商效能比較

### LLM 供應商比較

| 供應商 | 平均延遲 | P95 |
|--------|---------|-----|
| **OpenAI** | 1.2s | 2.1s |
| **Anthropic** | 1.5s | 2.8s |
| **Gemini** | 0.9s | 1.8s |

**注意**：
- 延遲包含網路 + 處理
- LLM 定價經常變動，請查閱各供應商官網取得最新價格

---

## ⚡ 最佳化建議

### 低延遲

1. **啟用 System 1 快取**
   ```yaml
   cognitive_features:
     system1:
       enable_cache: true
   ```

2. **使用適當模式**
   - 簡單查詢 → `chat`（System 1）
   - 複雜查詢 → `thinking`（System 2）
   - 避免對簡單任務使用 `deep_research`

3. **地理鄰近性**
   - 部署在靠近 LLM 供應商資料中心的位置

### 高吞吐量

1. **水平擴展**
   ```bash
   kubectl autoscale deployment opencode-api \
     --min=3 --max=10 --cpu-percent=70
   ```

2. **非同步處理**
   - 對長時間查詢使用 SSE 串流
   - 實作請求佇列以處理突發流量

### 成本效益

1. **積極快取** — System 1 模式可大幅節省
2. **智慧供應商選擇** — 備援至較便宜的供應商
3. **Token 最佳化** — System 1 使用較短的提示

---

## 🧪 基準重現

### 執行自己的測試

```bash
# 安裝相依套件
uv pip install locust

# 執行基準測試
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10
```

### Locust 測試範例

```python
from locust import HttpUser, task, between

class OpenCodeUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.post("/api/v1/auth/token", json={
            "username": "user",
            "password": "pass"
        })
        self.token = response.json()["access_token"]

    @task(3)
    def chat_query(self):
        self.client.post("/api/v1/chat",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"query": "Hello", "mode": "chat"}
        )

    @task(1)
    def thinking_query(self):
        self.client.post("/api/v1/chat",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"query": "解釋量子計算", "mode": "thinking"}
        )
```

---

## 📊 版本效能趨勢

| 版本 | System 1 延遲 | System 2 延遲 |
|------|--------------|--------------|
| v1.0.0 | 120ms | 2.8s |
| v1.5.0 | 67ms | 2.1s |
| v2.0.0 | 45ms | 1.2s |
| v3.x | 45ms | 1.2s |

**改善（v1.0 → v3.x）**：
- System 1：**62% 更快**
- System 2：**57% 更快**

---

## 📞 效能支援

遇到效能問題？

- [GitHub Discussions](https://github.com/Zenobia000/openagent_backend/discussions)
- [回報慢查詢](https://github.com/Zenobia000/openagent_backend/issues/new)

---

**返回**：[README](../README.md) | [文件](../README.md#-文件)
