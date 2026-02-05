"""
插件 API 路由
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from opencode.auth import get_current_user, require_admin, TokenData
from .manager import get_plugin_manager, PluginManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plugins", tags=["插件"])


class PluginConfigUpdate(BaseModel):
    """插件配置更新"""
    config: Dict[str, Any]


class GitInstallRequest(BaseModel):
    """Git 安裝請求"""
    url: str
    branch: str = "main"


@router.get("")
async def list_plugins(
    current_user: TokenData = Depends(get_current_user),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """列出所有插件"""
    return {
        "plugins": plugin_manager.list_plugins(),
        "count": len(plugin_manager._metadata)
    }


@router.get("/{plugin_id}")
async def get_plugin(
    plugin_id: str,
    current_user: TokenData = Depends(get_current_user),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """取得單個插件詳情"""
    metadata = plugin_manager._metadata.get(plugin_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
    
    plugin = plugin_manager._plugins.get(plugin_id)
    config = plugin_manager._configs.get(plugin_id, {})
    
    return {
        **metadata.to_dict(),
        "status": plugin.status.value if plugin else "discovered",
        "config": config
    }


@router.post("/discover")
async def discover_plugins(
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """發現插件（僅管理員）"""
    discovered = plugin_manager.discover_plugins()
    return {
        "discovered": [p.to_dict() for p in discovered],
        "count": len(discovered)
    }


@router.post("/upload")
async def upload_plugin(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """
    上傳並安裝插件 ZIP（僅管理員）
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")
    
    try:
        # 保存到臨時文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        # 安裝
        plugin_id = await plugin_manager.install_from_zip(tmp_path)
        
        # 清理
        tmp_path.unlink()
        
        if not plugin_id:
            raise HTTPException(status_code=400, detail="Failed to install plugin")
        
        return {
            "message": f"Plugin {plugin_id} installed",
            "plugin_id": plugin_id
        }
        
    except Exception as e:
        logger.error(f"Upload plugin error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install-git")
async def install_from_git(
    request: GitInstallRequest,
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """從 Git 安裝插件（僅管理員）"""
    plugin_id = await plugin_manager.install_from_git(request.url, request.branch)
    
    if not plugin_id:
        raise HTTPException(status_code=400, detail="Failed to install plugin from Git")
    
    return {
        "message": f"Plugin {plugin_id} installed from Git",
        "plugin_id": plugin_id
    }


@router.post("/{plugin_id}/load")
async def load_plugin(
    plugin_id: str,
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """載入插件（僅管理員）"""
    success = await plugin_manager.load_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to load plugin: {plugin_id}")
    return {"message": f"Plugin {plugin_id} loaded"}


@router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """啟用插件（僅管理員）"""
    # 確保已載入
    if plugin_id not in plugin_manager._plugins:
        await plugin_manager.load_plugin(plugin_id)
    
    success = await plugin_manager.enable_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to enable plugin: {plugin_id}")
    return {"message": f"Plugin {plugin_id} enabled"}


@router.post("/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """禁用插件（僅管理員）"""
    success = await plugin_manager.disable_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to disable plugin: {plugin_id}")
    return {"message": f"Plugin {plugin_id} disabled"}


@router.post("/{plugin_id}/reload")
async def reload_plugin(
    plugin_id: str,
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """熱重載插件（僅管理員）"""
    success = await plugin_manager.reload_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to reload plugin: {plugin_id}")
    return {"message": f"Plugin {plugin_id} reloaded"}


@router.delete("/{plugin_id}")
async def delete_plugin(
    plugin_id: str,
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """刪除插件（僅管理員）"""
    success = await plugin_manager.delete_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to delete plugin: {plugin_id}")
    return {"message": f"Plugin {plugin_id} deleted"}


@router.get("/{plugin_id}/config")
async def get_plugin_config(
    plugin_id: str,
    current_user: TokenData = Depends(get_current_user),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """取得插件配置"""
    metadata = plugin_manager._metadata.get(plugin_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
    
    return {
        "plugin_id": plugin_id,
        "config": plugin_manager._configs.get(plugin_id, {}),
        "schema": metadata.config_schema
    }


@router.put("/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    update: PluginConfigUpdate,
    current_user: TokenData = Depends(require_admin),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """更新插件配置（僅管理員）"""
    plugin_manager.set_plugin_config(plugin_id, update.config)
    return {"message": f"Plugin {plugin_id} config updated"}


@router.get("/tools/all")
async def get_plugin_tools(
    current_user: TokenData = Depends(get_current_user),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """取得所有插件提供的工具"""
    return {
        "tools": plugin_manager.get_all_tools()
    }


@router.get("/agents/all")
async def get_plugin_agents(
    current_user: TokenData = Depends(get_current_user),
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """取得所有插件提供的 Agents"""
    agents = plugin_manager.get_agent_plugins()
    return {
        "agents": [
            {
                "name": agent.agent_name,
                "description": agent.agent_description,
                "plugin_id": agent.metadata.id,
                "tools": agent.get_tools()
            }
            for agent in agents.values()
        ]
    }


@router.post("/refresh-agents")
async def refresh_plugin_agents(
    current_user: TokenData = Depends(require_admin)
):
    """
    刷新 Coordinator 中的插件 Agent（熱重載）
    
    當插件啟用/停用/更新後，調用此 API 讓 Coordinator 重新載入
    """
    try:
        from opencode.agents.coordinator import get_coordinator
        
        coordinator = await get_coordinator()
        await coordinator.reload_plugin_agents()
        
        return {
            "message": "Plugin agents refreshed",
            "agents": coordinator.list_agents()
        }
    except Exception as e:
        logger.error(f"Failed to refresh plugin agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
