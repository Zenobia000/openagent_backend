"""
Tests for PackageManager, PackageManifest, and dynamic registration
"""

import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.package_manifest import (
    PackageManifest,
    PackageInfo,
    PackageStatus,
    load_package_manifest,
)
from src.core.package_manager import PackageManager


# ============================================================
# PackageManifest Tests
# ============================================================

class TestPackageManifest:
    def test_valid_mcp_server_manifest(self):
        m = PackageManifest(
            id="weather",
            name="Weather Tool",
            type="mcp-server",
            transport="stdio",
            command="python",
            args=["server.py"],
        )
        assert m.id == "weather"
        assert m.type == "mcp-server"
        assert m.auto_start is True
        assert m.max_restarts == 3

    def test_valid_a2a_agent_manifest(self):
        m = PackageManifest(
            id="stock-analyst",
            name="Stock Analyst",
            type="a2a-agent",
            command="python",
            args=["server.py"],
            port=9001,
        )
        assert m.type == "a2a-agent"
        assert m.port == 9001

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="type"):
            PackageManifest(id="bad", name="Bad", type="invalid")

    def test_missing_required_fields(self):
        with pytest.raises(Exception):
            PackageManifest(name="No ID")

    def test_defaults(self):
        m = PackageManifest(id="x", name="X", type="mcp-server")
        assert m.version == "1.0.0"
        assert m.description == ""
        assert m.dependencies == []
        assert m.tags == []


class TestLoadPackageManifest:
    def test_load_valid_manifest(self, tmp_path):
        manifest_file = tmp_path / "package.yaml"
        manifest_file.write_text(
            "id: test-pkg\nname: Test Package\ntype: mcp-server\n"
            "transport: stdio\ncommand: python\nargs: [server.py]\n"
        )
        m = load_package_manifest(manifest_file)
        assert m.id == "test-pkg"
        assert m.type == "mcp-server"

    def test_load_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_package_manifest(tmp_path / "nope.yaml")

    def test_env_var_expansion(self, tmp_path):
        os.environ["TEST_PKG_KEY"] = "secret123"
        try:
            manifest_file = tmp_path / "package.yaml"
            manifest_file.write_text(
                "id: test\nname: Test\ntype: mcp-server\n"
                "env:\n  API_KEY: ${TEST_PKG_KEY}\n"
            )
            m = load_package_manifest(manifest_file)
            assert m.env["API_KEY"] == "secret123"
        finally:
            del os.environ["TEST_PKG_KEY"]

    def test_invalid_yaml_raises(self, tmp_path):
        manifest_file = tmp_path / "package.yaml"
        manifest_file.write_text("id: test\nname: Test\ntype: bad-type\n")
        with pytest.raises(ValueError):
            load_package_manifest(manifest_file)


class TestPackageInfo:
    def test_default_status(self):
        m = PackageManifest(id="x", name="X", type="mcp-server")
        info = PackageInfo(manifest=m, path=Path("/tmp/x"))
        assert info.status == PackageStatus.STOPPED
        assert info.error is None
        assert info.restart_count == 0


# ============================================================
# PackageManager Tests
# ============================================================

def _make_package_dir(base: Path, pkg_id: str, pkg_type: str = "mcp-server", **extra) -> Path:
    """Helper to create a package directory with package.yaml"""
    pkg_dir = base / pkg_id
    pkg_dir.mkdir()
    fields = {"id": pkg_id, "name": pkg_id, "type": pkg_type, **extra}
    lines = [f"{k}: {v}" for k, v in fields.items() if not isinstance(v, (list, dict))]
    (pkg_dir / "package.yaml").write_text("\n".join(lines) + "\n")
    return pkg_dir


class TestPackageManagerScan:
    @pytest.mark.asyncio
    async def test_scan_empty_dir(self, tmp_path):
        pm = PackageManager(tmp_path)
        result = await pm.scan_packages()
        assert result == []

    @pytest.mark.asyncio
    async def test_scan_nonexistent_dir(self, tmp_path):
        pm = PackageManager(tmp_path / "nope")
        result = await pm.scan_packages()
        assert result == []

    @pytest.mark.asyncio
    async def test_scan_finds_packages(self, tmp_path):
        _make_package_dir(tmp_path, "pkg-a")
        _make_package_dir(tmp_path, "pkg-b", pkg_type="a2a-agent")
        pm = PackageManager(tmp_path)
        result = await pm.scan_packages()
        assert len(result) == 2
        ids = {r.manifest.id for r in result}
        assert ids == {"pkg-a", "pkg-b"}

    @pytest.mark.asyncio
    async def test_scan_skips_invalid(self, tmp_path):
        _make_package_dir(tmp_path, "good")
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "package.yaml").write_text("id: bad\nname: Bad\ntype: invalid\n")
        pm = PackageManager(tmp_path)
        result = await pm.scan_packages()
        assert len(result) == 1
        assert result[0].manifest.id == "good"

    @pytest.mark.asyncio
    async def test_scan_skips_dirs_without_manifest(self, tmp_path):
        (tmp_path / "no-manifest").mkdir()
        _make_package_dir(tmp_path, "has-manifest")
        pm = PackageManager(tmp_path)
        result = await pm.scan_packages()
        assert len(result) == 1


class TestPackageManagerLifecycle:
    @pytest.mark.asyncio
    async def test_start_mcp_package(self, tmp_path):
        _make_package_dir(tmp_path, "mcp-pkg", transport="stdio", command="echo")
        mcp_client = AsyncMock()
        mcp_client.add_server = AsyncMock(return_value=True)
        pm = PackageManager(tmp_path, mcp_client=mcp_client)
        await pm.scan_packages()
        await pm.start_package("mcp-pkg")
        mcp_client.add_server.assert_called_once()
        info = pm._packages["mcp-pkg"]
        assert info.status == PackageStatus.RUNNING

    @pytest.mark.asyncio
    async def test_start_a2a_package(self, tmp_path):
        _make_package_dir(tmp_path, "a2a-pkg", pkg_type="a2a-agent", command="echo", port="9001")
        a2a_client = AsyncMock()
        a2a_client.add_agent = AsyncMock(return_value=True)
        pm = PackageManager(tmp_path, a2a_client=a2a_client)
        await pm.scan_packages()
        await pm.start_package("a2a-pkg")
        a2a_client.add_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_unknown_package_raises(self, tmp_path):
        pm = PackageManager(tmp_path)
        with pytest.raises(KeyError):
            await pm.start_package("nonexistent")

    @pytest.mark.asyncio
    async def test_start_mcp_without_client_raises(self, tmp_path):
        _make_package_dir(tmp_path, "mcp-pkg", transport="stdio", command="echo")
        pm = PackageManager(tmp_path)
        await pm.scan_packages()
        with pytest.raises(RuntimeError, match="MCP client not available"):
            await pm.start_package("mcp-pkg")

    @pytest.mark.asyncio
    async def test_stop_package(self, tmp_path):
        _make_package_dir(tmp_path, "mcp-pkg", transport="stdio", command="echo")
        mcp_client = AsyncMock()
        mcp_client.add_server = AsyncMock(return_value=True)
        mcp_client.remove_server = AsyncMock(return_value=True)
        pm = PackageManager(tmp_path, mcp_client=mcp_client)
        await pm.scan_packages()
        await pm.start_package("mcp-pkg")
        await pm.stop_package("mcp-pkg")
        mcp_client.remove_server.assert_called_once_with("mcp-pkg")
        assert pm._packages["mcp-pkg"].status == PackageStatus.STOPPED

    @pytest.mark.asyncio
    async def test_start_all_auto_start(self, tmp_path):
        _make_package_dir(tmp_path, "auto-pkg", transport="stdio", command="echo")
        # Create a non-auto-start package
        pkg_dir = tmp_path / "manual-pkg"
        pkg_dir.mkdir()
        (pkg_dir / "package.yaml").write_text(
            "id: manual-pkg\nname: Manual\ntype: mcp-server\nauto_start: false\n"
        )
        mcp_client = AsyncMock()
        mcp_client.add_server = AsyncMock(return_value=True)
        pm = PackageManager(tmp_path, mcp_client=mcp_client)
        await pm.start_all()
        # Only auto-pkg should have been started
        assert mcp_client.add_server.call_count == 1

    @pytest.mark.asyncio
    async def test_failed_start_records_error(self, tmp_path):
        _make_package_dir(tmp_path, "fail-pkg", transport="stdio", command="echo")
        mcp_client = AsyncMock()
        mcp_client.add_server = AsyncMock(side_effect=RuntimeError("connection refused"))
        pm = PackageManager(tmp_path, mcp_client=mcp_client)
        await pm.scan_packages()
        with pytest.raises(RuntimeError):
            await pm.start_package("fail-pkg")
        info = pm._packages["fail-pkg"]
        assert info.status == PackageStatus.FAILED
        assert "connection refused" in info.error
        assert info.restart_count == 1


class TestPackageManagerList:
    @pytest.mark.asyncio
    async def test_list_packages(self, tmp_path):
        _make_package_dir(tmp_path, "pkg-a")
        pm = PackageManager(tmp_path)
        await pm.scan_packages()
        result = await pm.list_packages()
        assert len(result) == 1
        assert result[0]["id"] == "pkg-a"
        assert result[0]["status"] == "stopped"


class TestPackageManagerShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_stops_running(self, tmp_path):
        _make_package_dir(tmp_path, "pkg", transport="stdio", command="echo")
        mcp_client = AsyncMock()
        mcp_client.add_server = AsyncMock(return_value=True)
        mcp_client.remove_server = AsyncMock(return_value=True)
        pm = PackageManager(tmp_path, mcp_client=mcp_client)
        await pm.scan_packages()
        await pm.start_package("pkg")
        await pm.shutdown()
        mcp_client.remove_server.assert_called_once()
        assert len(pm._packages) == 0


# ============================================================
# Engine Integration (no packages dir → no error)
# ============================================================

class TestEngineIntegration:
    @pytest.mark.asyncio
    async def test_package_manager_no_packages_dir(self, tmp_path):
        """PackageManager with nonexistent dir should not error"""
        pm = PackageManager(tmp_path / "nonexistent")
        await pm.start_all()  # should silently do nothing
        result = await pm.list_packages()
        assert result == []
