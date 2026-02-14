"""
Package Manager — 掃描 packages/ 目錄，動態註冊 MCP servers / A2A agents
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import structured_logger
from .package_manifest import (
    PackageInfo,
    PackageManifest,
    PackageStatus,
    load_package_manifest,
)

logger = structured_logger


class PackageManager:
    """統一管理 packages/ 目錄下的 MCP Servers 和 A2A Agents"""

    def __init__(self, packages_dir: Path, mcp_client=None, a2a_client=None):
        self._packages_dir = packages_dir
        self._mcp_client = mcp_client
        self._a2a_client = a2a_client
        self._packages: Dict[str, PackageInfo] = {}

    async def scan_packages(self) -> List[PackageInfo]:
        """掃描 packages/ 目錄，解析所有 package.yaml manifests"""
        if not self._packages_dir.exists():
            return []

        packages = []
        for child in sorted(self._packages_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = child / "package.yaml"
            if not manifest_path.exists():
                continue
            try:
                manifest = load_package_manifest(manifest_path)
                info = PackageInfo(manifest=manifest, path=child)
                self._packages[manifest.id] = info
                packages.append(info)
            except Exception as e:
                logger.warning(f"Failed to load package from {child}: {e}")

        return packages

    async def start_package(self, package_id: str) -> None:
        """Convert manifest to config and register dynamically"""
        if package_id not in self._packages:
            raise KeyError(f"Package '{package_id}' not found")

        info = self._packages[package_id]
        manifest = info.manifest
        info.status = PackageStatus.STARTING

        try:
            if manifest.type == "mcp-server":
                await self._start_mcp_package(manifest, info)
            elif manifest.type == "a2a-agent":
                await self._start_a2a_package(manifest, info)

            info.status = PackageStatus.RUNNING
            logger.info(f"Package '{package_id}' started", package_id=package_id, type=manifest.type)
        except Exception as e:
            info.status = PackageStatus.FAILED
            info.error = str(e)
            info.restart_count += 1
            logger.warning(f"Package '{package_id}' failed to start: {e}", package_id=package_id)
            raise

    async def _start_mcp_package(self, manifest: PackageManifest, info: PackageInfo) -> None:
        """Register an MCP server package"""
        if not self._mcp_client:
            raise RuntimeError("MCP client not available")

        from .mcp_client import MCPServerConfig

        config = MCPServerConfig(
            name=manifest.id,
            transport=manifest.transport or "stdio",
            command=manifest.command,
            args=manifest.args,
            env=manifest.env,
            cwd=manifest.cwd or str(info.path),
            url=manifest.url,
            headers=manifest.headers,
        )
        await self._mcp_client.add_server(config)

    async def _start_a2a_package(self, manifest: PackageManifest, info: PackageInfo) -> None:
        """Register an A2A agent package"""
        if not self._a2a_client:
            raise RuntimeError("A2A client not available")

        from .a2a_client import A2AAgentConfig

        config = A2AAgentConfig(
            name=manifest.id,
            type="local" if manifest.command else "remote",
            command=manifest.command,
            args=manifest.args,
            port=manifest.port,
            env=manifest.env,
            url=manifest.url,
            auth_token=manifest.auth_token,
        )
        await self._a2a_client.add_agent(config)

    async def stop_package(self, package_id: str) -> None:
        """Unregister from MCP/A2A client"""
        if package_id not in self._packages:
            raise KeyError(f"Package '{package_id}' not found")

        info = self._packages[package_id]
        manifest = info.manifest

        try:
            if manifest.type == "mcp-server" and self._mcp_client:
                await self._mcp_client.remove_server(manifest.id)
            elif manifest.type == "a2a-agent" and self._a2a_client:
                await self._a2a_client.remove_agent(manifest.id)

            info.status = PackageStatus.STOPPED
            info.error = None
            logger.info(f"Package '{package_id}' stopped", package_id=package_id)
        except Exception as e:
            logger.warning(f"Error stopping package '{package_id}': {e}", package_id=package_id)
            raise

    async def start_all(self) -> None:
        """Scan and start all auto_start=true packages"""
        packages = await self.scan_packages()
        for info in packages:
            if info.manifest.auto_start:
                try:
                    await self.start_package(info.manifest.id)
                except Exception as e:
                    logger.warning(
                        f"Package '{info.manifest.id}' auto-start failed: {e}",
                        package_id=info.manifest.id,
                    )

    async def list_packages(self) -> List[Dict[str, Any]]:
        """List all packages with status"""
        result = []
        for pkg_id, info in self._packages.items():
            result.append({
                "id": pkg_id,
                "name": info.manifest.name,
                "version": info.manifest.version,
                "type": info.manifest.type,
                "status": info.status.value,
                "error": info.error,
                "path": str(info.path),
            })
        return result

    async def shutdown(self) -> None:
        """Stop all running packages"""
        for pkg_id, info in list(self._packages.items()):
            if info.status == PackageStatus.RUNNING:
                try:
                    await self.stop_package(pkg_id)
                except Exception as e:
                    logger.warning(f"Error during shutdown of '{pkg_id}': {e}")
        self._packages.clear()
