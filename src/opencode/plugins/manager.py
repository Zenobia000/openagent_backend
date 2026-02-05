"""
插件系統 - 支援第三方擴展

功能:
- 插件發現和載入
- 生命週期管理
- 鉤子系統
- 依賴管理
"""

import os
import sys
import json
import logging
import importlib
import importlib.util
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from opencode.core.utils import get_project_root

logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """插件類型"""
    AGENT = "agent"         # Agent 插件（新增 Agent）
    TOOL = "tool"           # 工具插件（新增工具）
    SERVICE = "service"     # 服務插件（新增 MCP 服務）
    PROCESSOR = "processor" # 處理器插件（文件處理）
    UI = "ui"               # UI 插件（前端組件）
    HOOK = "hook"           # 鉤子插件（事件監聽）


class PluginStatus(str, Enum):
    """插件狀態"""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """插件元資料"""
    id: str                         # 唯一識別符
    name: str                       # 顯示名稱
    version: str                    # 版本號
    description: str = ""           # 描述
    author: str = ""                # 作者
    plugin_type: PluginType = PluginType.TOOL
    dependencies: List[str] = field(default_factory=list)  # 依賴的其他插件
    python_requires: str = ">=3.9"  # Python 版本要求
    entry_point: str = "main"       # 入口模組
    config_schema: Dict = field(default_factory=dict)  # 配置結構
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["plugin_type"] = self.plugin_type.value
        return data


class Plugin(ABC):
    """
    插件基類
    
    所有插件必須繼承此類
    """
    
    def __init__(self, metadata: PluginMetadata, config: Dict[str, Any] = None):
        self.metadata = metadata
        self.config = config or {}
        self.status = PluginStatus.LOADED
    
    @abstractmethod
    async def on_load(self) -> None:
        """插件載入時調用"""
        pass
    
    @abstractmethod
    async def on_enable(self) -> None:
        """插件啟用時調用"""
        pass
    
    async def on_disable(self) -> None:
        """插件禁用時調用"""
        pass
    
    async def on_unload(self) -> None:
        """插件卸載時調用"""
        pass
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """返回插件提供的工具列表"""
        return []
    
    def get_hooks(self) -> Dict[str, Callable]:
        """返回插件的鉤子函數"""
        return {}


class ToolPlugin(Plugin):
    """工具插件基類"""
    
    @abstractmethod
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """執行工具"""
        pass


class ServicePlugin(Plugin):
    """服務插件基類"""
    
    @abstractmethod
    async def start_service(self) -> None:
        """啟動服務"""
        pass
    
    @abstractmethod
    async def stop_service(self) -> None:
        """停止服務"""
        pass


class AgentPlugin(Plugin):
    """
    Agent 插件基類
    
    繼承此類來創建自定義 Agent
    """
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Agent 名稱"""
        pass
    
    @property
    def agent_description(self) -> str:
        """Agent 描述"""
        return self.metadata.description
    
    @property
    def system_prompt(self) -> str:
        """Agent 的系統提示詞"""
        return f"你是 {self.agent_name}，{self.agent_description}"
    
    @abstractmethod
    async def process_task(self, task_description: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        處理任務
        
        Args:
            task_description: 任務描述
            parameters: 任務參數
            context: 上下文（如 selected_docs, attachments 等）
            
        Returns:
            {
                "success": bool,
                "output": Any,
                "error": Optional[str]
            }
        """
        pass
    
    def get_tools(self) -> List[str]:
        """
        返回此 Agent 可使用的工具列表
        
        Returns:
            工具名稱列表，如 ["rag_search", "code_execute"]
        """
        return []


class PluginManager:
    """
    插件管理器
    
    負責:
    - 發現插件
    - 載入/卸載插件
    - 管理插件生命週期
    - 執行鉤子
    """
    
    def __init__(self):
        self.plugins_dir = get_project_root() / "plugins"
        self.plugins_dir.mkdir(exist_ok=True)
        
        self._plugins: Dict[str, Plugin] = {}
        self._metadata: Dict[str, PluginMetadata] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        
        # 插件配置存儲
        self._config_file = get_project_root() / "data" / "plugins_config.json"
        self._configs: Dict[str, Dict] = {}
        self._load_configs()
        
        logger.info(f"✅ PluginManager initialized, plugins_dir: {self.plugins_dir}")
    
    def _load_configs(self) -> None:
        """載入插件配置"""
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._configs = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load plugin configs: {e}")
    
    def _save_configs(self) -> None:
        """保存插件配置"""
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._configs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plugin configs: {e}")
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """
        發現可用插件
        
        掃描 plugins 目錄，讀取每個插件的 plugin.json
        """
        discovered = []
        
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                manifest_file = item / "plugin.json"
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        metadata = PluginMetadata(
                            id=data.get("id", item.name),
                            name=data.get("name", item.name),
                            version=data.get("version", "0.0.1"),
                            description=data.get("description", ""),
                            author=data.get("author", ""),
                            plugin_type=PluginType(data.get("type", "tool")),
                            dependencies=data.get("dependencies", []),
                            entry_point=data.get("entry_point", "main"),
                            config_schema=data.get("config_schema", {})
                        )
                        
                        self._metadata[metadata.id] = metadata
                        discovered.append(metadata)
                        logger.info(f"📦 Discovered plugin: {metadata.name} v{metadata.version}")
                        
                    except Exception as e:
                        logger.error(f"Failed to read plugin manifest {manifest_file}: {e}")
        
        return discovered
    
    async def load_plugin(self, plugin_id: str) -> bool:
        """載入插件"""
        if plugin_id in self._plugins:
            logger.warning(f"Plugin {plugin_id} already loaded")
            return True
        
        metadata = self._metadata.get(plugin_id)
        if not metadata:
            logger.error(f"Plugin {plugin_id} not found")
            return False
        
        try:
            # 安裝 Python 依賴（如果有）
            plugin_dir = self.plugins_dir / plugin_id
            requirements_file = plugin_dir / "requirements.txt"
            if requirements_file.exists():
                await self._install_requirements(requirements_file)
            
            # 嘗試導入依賴的 Python 包
            for dep in metadata.dependencies:
                try:
                    __import__(dep.split('>=')[0].split('==')[0].strip())
                except ImportError:
                    logger.warning(f"⚠️ Optional dependency {dep} not available for {plugin_id}")
            
            # 載入模組
            plugin_path = self.plugins_dir / plugin_id / f"{metadata.entry_point}.py"
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_id}.{metadata.entry_point}",
                plugin_path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # 取得插件類
            plugin_class = getattr(module, "PluginImpl", None)
            if not plugin_class or not issubclass(plugin_class, Plugin):
                raise ValueError(f"PluginImpl class not found in {plugin_path}")
            
            # 實例化
            config = self._configs.get(plugin_id, {})
            plugin = plugin_class(metadata, config)
            
            # 調用載入鉤子
            await plugin.on_load()
            
            self._plugins[plugin_id] = plugin
            logger.info(f"✅ Loaded plugin: {metadata.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """啟用插件"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        try:
            await plugin.on_enable()
            plugin.status = PluginStatus.ENABLED
            
            # 註冊鉤子
            for hook_name, handler in plugin.get_hooks().items():
                if hook_name not in self._hooks:
                    self._hooks[hook_name] = []
                self._hooks[hook_name].append(handler)
            
            logger.info(f"✅ Enabled plugin: {plugin.metadata.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable plugin {plugin_id}: {e}")
            plugin.status = PluginStatus.ERROR
            return False
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        try:
            await plugin.on_disable()
            plugin.status = PluginStatus.DISABLED
            
            # 移除鉤子
            for hook_name, handler in plugin.get_hooks().items():
                if hook_name in self._hooks and handler in self._hooks[hook_name]:
                    self._hooks[hook_name].remove(handler)
            
            logger.info(f"🔌 Disabled plugin: {plugin.metadata.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable plugin {plugin_id}: {e}")
            return False
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """卸載插件"""
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_id]
        
        try:
            if plugin.status == PluginStatus.ENABLED:
                await self.disable_plugin(plugin_id)
            
            await plugin.on_unload()
            del self._plugins[plugin_id]
            
            logger.info(f"🗑️ Unloaded plugin: {plugin.metadata.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False
    
    async def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """觸發鉤子"""
        results = []
        handlers = self._hooks.get(hook_name, [])
        
        for handler in handlers:
            try:
                result = await handler(*args, **kwargs) if asyncio.iscoroutinefunction(handler) else handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook_name} handler error: {e}")
        
        return results
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """取得插件實例"""
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有插件"""
        result = []
        for plugin_id, metadata in self._metadata.items():
            plugin = self._plugins.get(plugin_id)
            result.append({
                **metadata.to_dict(),
                "status": plugin.status.value if plugin else "discovered"
            })
        return result
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """取得所有插件提供的工具"""
        tools = []
        for plugin in self._plugins.values():
            if plugin.status == PluginStatus.ENABLED:
                tools.extend(plugin.get_tools())
        return tools
    
    def set_plugin_config(self, plugin_id: str, config: Dict[str, Any]) -> None:
        """設置插件配置"""
        self._configs[plugin_id] = config
        self._save_configs()
        
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.config = config
    
    async def reload_plugin(self, plugin_id: str) -> bool:
        """
        熱重載插件（不需重啟服務）
        
        1. 卸載現有插件
        2. 重新載入模組
        3. 重新啟用插件
        """
        if plugin_id not in self._metadata:
            logger.error(f"Plugin {plugin_id} not found")
            return False
        
        was_enabled = False
        if plugin_id in self._plugins:
            was_enabled = self._plugins[plugin_id].status == PluginStatus.ENABLED
            await self.unload_plugin(plugin_id)
        
        # 清除模組快取
        metadata = self._metadata[plugin_id]
        module_name = f"plugins.{plugin_id}.{metadata.entry_point}"
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        # 重新載入
        success = await self.load_plugin(plugin_id)
        if success and was_enabled:
            await self.enable_plugin(plugin_id)
        
        logger.info(f"🔄 Reloaded plugin: {metadata.name}")
        return success
    
    async def install_from_zip(self, zip_path: Path) -> Optional[str]:
        """
        從 ZIP 檔案安裝插件
        
        Returns:
            插件 ID 或 None（失敗時）
        """
        import zipfile
        import shutil
        import tempfile
        
        try:
            # 解壓到臨時目錄
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # 尋找 plugin.json
                temp_path = Path(temp_dir)
                manifest_files = list(temp_path.rglob("plugin.json"))
                
                if not manifest_files:
                    raise ValueError("plugin.json not found in zip")
                
                manifest_file = manifest_files[0]
                plugin_dir = manifest_file.parent
                
                # 讀取 manifest
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                plugin_id = manifest.get("id", plugin_dir.name)
                
                # 複製到 plugins 目錄
                target_dir = self.plugins_dir / plugin_id
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                
                shutil.copytree(plugin_dir, target_dir)
                
                # 安裝依賴
                requirements_file = target_dir / "requirements.txt"
                if requirements_file.exists():
                    await self._install_requirements(requirements_file)
                
                # 重新發現插件
                self.discover_plugins()
                
                logger.info(f"📦 Installed plugin from zip: {plugin_id}")
                return plugin_id
                
        except Exception as e:
            logger.error(f"Failed to install plugin from zip: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def install_from_git(self, git_url: str, branch: str = "main") -> Optional[str]:
        """
        從 Git 倉庫安裝插件
        
        Returns:
            插件 ID 或 None（失敗時）
        """
        import subprocess
        import tempfile
        import shutil
        
        try:
            # Clone 到臨時目錄
            with tempfile.TemporaryDirectory() as temp_dir:
                subprocess.run(
                    ["git", "clone", "--depth=1", "-b", branch, git_url, temp_dir],
                    check=True,
                    capture_output=True
                )
                
                temp_path = Path(temp_dir)
                manifest_file = temp_path / "plugin.json"
                
                if not manifest_file.exists():
                    raise ValueError("plugin.json not found in repository")
                
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                plugin_id = manifest.get("id", temp_path.name)
                
                # 複製到 plugins 目錄（排除 .git）
                target_dir = self.plugins_dir / plugin_id
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                
                shutil.copytree(
                    temp_path, 
                    target_dir,
                    ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc')
                )
                
                # 安裝依賴
                requirements_file = target_dir / "requirements.txt"
                if requirements_file.exists():
                    await self._install_requirements(requirements_file)
                
                # 重新發現插件
                self.discover_plugins()
                
                logger.info(f"📦 Installed plugin from git: {plugin_id}")
                return plugin_id
                
        except Exception as e:
            logger.error(f"Failed to install plugin from git: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def _install_requirements(self, requirements_file: Path) -> None:
        """安裝 Python 依賴"""
        import subprocess
        
        logger.info(f"📦 Installing requirements from {requirements_file}")
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning(f"Failed to install some requirements: {result.stderr}")
    
    async def delete_plugin(self, plugin_id: str) -> bool:
        """刪除插件"""
        import shutil
        
        # 先卸載
        if plugin_id in self._plugins:
            await self.unload_plugin(plugin_id)
        
        # 刪除目錄
        plugin_dir = self.plugins_dir / plugin_id
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
        
        # 移除 metadata
        self._metadata.pop(plugin_id, None)
        self._configs.pop(plugin_id, None)
        self._save_configs()
        
        logger.info(f"🗑️ Deleted plugin: {plugin_id}")
        return True
    
    def get_agent_plugins(self) -> Dict[str, 'AgentPlugin']:
        """取得所有已啟用的 Agent 插件"""
        agents = {}
        for plugin_id, plugin in self._plugins.items():
            if (
                plugin.status == PluginStatus.ENABLED and 
                plugin.metadata.plugin_type == PluginType.AGENT and
                isinstance(plugin, AgentPlugin)
            ):
                agents[plugin.agent_name] = plugin
        return agents
    
    def get_tool_plugins(self) -> Dict[str, 'ToolPlugin']:
        """取得所有已啟用的 Tool 插件"""
        tools = {}
        for plugin_id, plugin in self._plugins.items():
            if (
                plugin.status == PluginStatus.ENABLED and 
                plugin.metadata.plugin_type == PluginType.TOOL and
                isinstance(plugin, ToolPlugin)
            ):
                tools[plugin_id] = plugin
        return tools


# 需要導入
import asyncio

# 全域實例
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """取得插件管理器實例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
