"""
Service Initializer - Extracted from Engine.initialize()

This module handles the initialization of external services with graceful degradation.
Each service is initialized independently with its own try/except block, so failures
in one service don't prevent others from starting.

Design Decision:
----------------
Extracted from Engine.initialize() to:
1. Reduce the complexity of the Engine class
2. Make service initialization logic testable independently
3. Allow reuse in other contexts (e.g., CLI tools, background workers)
4. Follow Single Responsibility Principle

The ServiceInitializer maintains the same graceful degradation behavior as before:
- Each service is optional
- Failures are logged but don't crash the application
- Services return None if unavailable
"""

from pathlib import Path
from typing import Dict, Any, Optional
from .logger import structured_logger


class ServiceInitializer:
    """Initializes external services with graceful degradation."""

    def __init__(self, logger=None):
        """
        Initialize the service initializer.

        Args:
            logger: Logger instance (defaults to structured_logger)
        """
        self.logger = logger or structured_logger

    async def initialize_all(self) -> Dict[str, Any]:
        """
        Initialize all external services.

        Returns:
            Dict[str, Any]: Dictionary of successfully initialized services
                           Keys are service names, values are service instances
        """
        services = {}

        # Initialize core services
        await self._init_search_service(services)
        await self._init_knowledge_service(services)
        await self._init_sandbox_service(services)

        return services

    async def _init_search_service(self, services: Dict[str, Any]) -> None:
        """Initialize web search service."""
        try:
            from services.search.service import get_web_search_service
            services["search"] = get_web_search_service()
            self.logger.info("Search service initialized")
        except Exception as e:
            self.logger.warning(f"Search service unavailable: {e}")

    async def _init_knowledge_service(self, services: Dict[str, Any]) -> None:
        """Initialize knowledge base service."""
        try:
            from services.knowledge.service import KnowledgeBaseService
            kb = KnowledgeBaseService()
            await kb.initialize()
            services["knowledge"] = kb
            self.logger.info("Knowledge service initialized")
        except Exception as e:
            self.logger.warning(f"Knowledge service unavailable: {e}")

    async def _init_sandbox_service(self, services: Dict[str, Any]) -> None:
        """Initialize code sandbox service."""
        try:
            from services.sandbox.service import SandboxService
            sandbox = SandboxService()
            await sandbox.initialize()
            services["sandbox"] = sandbox
            self.logger.info("Sandbox service initialized")
        except Exception as e:
            self.logger.warning(f"Sandbox service unavailable: {e}")

    async def initialize_mcp_client(self) -> Optional[Any]:
        """
        Initialize MCP client (Model Context Protocol - external tool servers).

        Returns:
            MCPClientManager instance or None if unavailable
        """
        try:
            from .mcp_client import MCPClientManager, load_mcp_config
            mcp_config = load_mcp_config()
            mcp_client = MCPClientManager(mcp_config)
            await mcp_client.initialize()
            if mcp_client.connected_servers:
                self.logger.info(
                    f"MCP client initialized ({len(mcp_client.connected_servers)} servers, "
                    f"{mcp_client.total_tools} tools)"
                )
                return mcp_client
            else:
                self.logger.warning("MCP client initialized but no servers connected")
                return None
        except Exception as e:
            self.logger.warning(f"MCP client unavailable: {e}")
            return None

    async def initialize_a2a_client(self) -> Optional[Any]:
        """
        Initialize A2A client (Agent-to-Agent - external agent collaboration).

        Returns:
            A2AClientManager instance or None if unavailable
        """
        try:
            from .a2a_client import A2AClientManager, load_a2a_config
            a2a_config = load_a2a_config()
            a2a_client = A2AClientManager(a2a_config)
            await a2a_client.initialize()
            if a2a_client.connected_agents:
                self.logger.info(
                    f"A2A client initialized ({len(a2a_client.connected_agents)} agents, "
                    f"{a2a_client.total_skills} skills)"
                )
                return a2a_client
            else:
                self.logger.warning("A2A client initialized but no agents connected")
                return None
        except Exception as e:
            self.logger.warning(f"A2A client unavailable: {e}")
            return None

    async def initialize_package_manager(
        self,
        packages_dir: Path,
        mcp_client: Optional[Any] = None,
        a2a_client: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Initialize PackageManager for dynamic package registration.

        Args:
            packages_dir: Directory containing packages
            mcp_client: Optional MCP client instance
            a2a_client: Optional A2A client instance

        Returns:
            PackageManager instance or None if unavailable
        """
        try:
            if not packages_dir.exists():
                self.logger.warning(f"Packages directory not found: {packages_dir}")
                return None

            from .package_manager import PackageManager
            package_manager = PackageManager(packages_dir, mcp_client, a2a_client)
            await package_manager.start_all()
            self.logger.info(f"PackageManager initialized from {packages_dir}")
            return package_manager
        except Exception as e:
            self.logger.warning(f"PackageManager unavailable: {e}")
            return None
