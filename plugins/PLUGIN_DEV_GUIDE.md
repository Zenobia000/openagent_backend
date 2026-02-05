# OpenCode 插件開發指南

## 📁 插件結構

```
plugins/
└── my-plugin/
    ├── plugin.json       # 必須：插件元數據
    ├── main.py           # 必須：主入口文件
    ├── requirements.txt  # 可選：Python 依賴
    ├── icon.png          # 可選：插件圖標
    └── README.md         # 可選：說明文檔
```

---

## 📋 plugin.json 規範

```json
{
  "id": "my-plugin",
  "name": "我的插件",
  "version": "1.0.0",
  "description": "插件描述",
  "author": "作者名稱",
  "type": "agent",
  "entry_point": "main",
  "class_name": "PluginImpl",
  
  "config_schema": {
    "api_key": {
      "type": "string",
      "label": "API Key",
      "required": true,
      "secret": true,
      "description": "說明文字"
    },
    "option": {
      "type": "select",
      "label": "選項",
      "options": ["A", "B", "C"],
      "default": "A"
    }
  },
  
  "permissions": ["network", "file_read"],
  "dependencies": ["requests", "pandas"],
  "tags": ["utility", "api"]
}
```

### 插件類型 (type)

| 類型 | 說明 |
|------|------|
| `agent` | Agent 插件，可被 Dispatcher 分配任務 |
| `tool` | 工具插件，提供新工具給 Agent 使用 |
| `service` | 服務插件，後台服務 |
| `hook` | 鉤子插件，監聽事件 |

### 配置欄位類型 (config_schema)

| 類型 | 說明 |
|------|------|
| `string` | 文字輸入 |
| `select` | 下拉選單 |
| `boolean` | 開關 |
| `number` | 數字 |

---

## 🤖 Agent 插件範例

```python
# main.py
from typing import Dict, Any, List
from opencode.plugins.manager import AgentPlugin, PluginMetadata

class PluginImpl(AgentPlugin):
    """我的 Agent 插件"""
    
    @property
    def agent_name(self) -> str:
        """Agent 唯一名稱（用於 Dispatcher 分配）"""
        return "my_agent"
    
    @property
    def agent_description(self) -> str:
        """Agent 描述"""
        return "這是我的自定義 Agent"
    
    @property
    def system_prompt(self) -> str:
        """Agent 系統提示詞"""
        return """你是一個專業的助手。
        
你的職責是：
1. 處理用戶請求
2. 提供專業建議

配置參數：
- API Key: {api_key}
""".format(api_key=self.config.get("api_key", "未設置"))
    
    async def on_load(self) -> None:
        """載入時調用"""
        print(f"📦 {self.metadata.name} 載入中...")
    
    async def on_enable(self) -> None:
        """啟用時調用"""
        print(f"✅ {self.metadata.name} 已啟用")
    
    async def on_disable(self) -> None:
        """禁用時調用"""
        print(f"🔌 {self.metadata.name} 已禁用")
    
    def get_tools(self) -> List[str]:
        """此 Agent 可用的工具列表"""
        return ["rag_search", "web_search"]
    
    async def process_task(
        self, 
        task_description: str, 
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        處理任務
        
        Args:
            task_description: 任務描述
            parameters: 任務參數
            context: 上下文（selected_docs, attachments 等）
            
        Returns:
            {"success": bool, "output": Any, "error": Optional[str]}
        """
        try:
            # 你的邏輯
            result = f"處理任務: {task_description}"
            
            return {
                "success": True,
                "output": {"result": result},
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }
```

---

## 🔧 Tool 插件範例

```python
# main.py
from typing import Dict, Any, List
from opencode.plugins.manager import ToolPlugin, PluginMetadata

class PluginImpl(ToolPlugin):
    """我的工具插件"""
    
    async def on_load(self) -> None:
        print(f"🔧 {self.metadata.name} 載入中...")
    
    async def on_enable(self) -> None:
        print(f"✅ {self.metadata.name} 已啟用")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """返回工具定義（OpenAI 格式）"""
        return [
            {
                "name": "my_tool",
                "description": "我的工具描述",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "輸入參數"
                        }
                    },
                    "required": ["input"]
                }
            }
        ]
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行工具
        
        Args:
            action: 工具名稱
            parameters: 工具參數
            
        Returns:
            執行結果
        """
        if action == "my_tool":
            return await self._my_tool(parameters.get("input", ""))
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def _my_tool(self, input: str) -> Dict[str, Any]:
        # 你的邏輯
        return {"result": f"處理: {input}"}
```

---

## 🔒 沙箱執行

插件代碼在沙箱中執行（如果 Docker 可用）：

- **記憶體限制**：512MB
- **CPU 限制**：1 核心
- **執行超時**：60 秒
- **網路**：需聲明 `network` 權限

---

## 📦 安裝插件

### 方法 1：放入 plugins 目錄

```bash
cp -r my-plugin/ plugins/
```

重啟後端或調用「發現插件」API。

### 方法 2：ZIP 上傳

將插件目錄打包成 ZIP，在 UI 中上傳。

### 方法 3：從 Git 安裝

```
https://github.com/user/my-plugin.git
```

---

## 🔄 熱重載

修改插件代碼後：

1. 在 UI 中點擊「🔄 重載」按鈕
2. 或調用 API: `POST /api/plugins/{plugin_id}/reload`

不需要重啟服務！

---

## 📡 API 參考

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/plugins` | GET | 列出所有插件 |
| `/api/plugins/discover` | POST | 發現插件 |
| `/api/plugins/upload` | POST | 上傳 ZIP 安裝 |
| `/api/plugins/install-git` | POST | 從 Git 安裝 |
| `/api/plugins/{id}/enable` | POST | 啟用插件 |
| `/api/plugins/{id}/disable` | POST | 停用插件 |
| `/api/plugins/{id}/reload` | POST | 熱重載 |
| `/api/plugins/{id}/config` | GET/PUT | 配置管理 |
| `/api/plugins/{id}` | DELETE | 刪除插件 |
| `/api/plugins/refresh-agents` | POST | 刷新 Coordinator |

---

## 🐛 除錯

查看日誌：

```bash
# 後端日誌
tail -f logs/opencode.log | grep -i plugin
```

常見問題：

1. **插件未發現**：檢查 `plugin.json` 是否存在且格式正確
2. **載入失敗**：檢查 `main.py` 中的 `PluginImpl` 類
3. **依賴缺失**：確保 `requirements.txt` 中列出所有依賴
