"""
Feature flags - Configuration-driven feature toggles.
Reads from config/cognitive_features.yaml with safe defaults.
"""

from pathlib import Path
from typing import Any, Optional
import yaml


_DEFAULT_CONFIG = {
    "cognitive_features": {
        "enabled": False,
        "system1": {
            "enable_cache": False,
            "cache_ttl": 300,
            "cache_max_size": 1000,
        },
        "system2": {
            "enable_thinking_chain": False,
            "max_thinking_time": 30,
            "reflection_depth": 3,
        },
        "routing": {
            "smart_routing": False,
            "complexity_analysis": False,
            "auto_mode_switch": False,
        },
        "metrics": {
            "cognitive_metrics": False,
            "detailed_tracking": False,
        },
        # Refactoring feature flags (Phase 0-7)
        "refactor": {
            "enabled": False,
            # Phase 1: Data models
            "new_data_models": False,
            "unified_event_model": False,
            # Phase 2: Processors
            "new_processor_structure": False,
            "processor_factory_v2": False,
            # Phase 3: Error handling
            "unified_error_handling": False,
            "strategy_execution": False,
            # Phase 4: Routing & Logging
            "pattern_based_routing": False,
            "unified_logging": False,
            # Phase 5: Cleanup
            "remove_unused_protocols": False,
            "simplified_initialization": False,
        },
        # Context Engineering (Manus-aligned)
        "context_engineering": {
            "enabled": False,
            "append_only_context": False,
            "todo_recitation": False,
            "error_preservation": False,
            "tool_masking": False,
            "template_randomizer": False,
            "file_based_memory": False,
            "file_memory_workspace": ".agent_workspace",
            "compress_keep_last": 10,
        },
    }
}


class FeatureFlags:
    """Configuration-driven feature flag manager"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "cognitive_features.yaml"
        self._config = self._load_config(config_path)

    def _load_config(self, path: Path) -> dict:
        """Load YAML config with fallback to defaults"""
        if path.exists():
            with open(path) as f:
                loaded = yaml.safe_load(f) or {}
            return self._deep_merge(_DEFAULT_CONFIG, loaded)
        return _DEFAULT_CONFIG.copy()

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge override into base, returning new dict"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = FeatureFlags._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @property
    def enabled(self) -> bool:
        """Master switch for all cognitive features"""
        return bool(self._get("cognitive_features.enabled"))

    def is_enabled(self, feature_path: str) -> bool:
        """Check if a feature is enabled.

        Args:
            feature_path: Dot-separated path, e.g. "system1.enable_cache"

        Returns:
            True only if master switch AND the specific feature are both enabled.
        """
        if not self.enabled:
            return False
        return bool(self._get(f"cognitive_features.{feature_path}"))

    def get_value(self, feature_path: str, default: Any = None) -> Any:
        """Get a config value by dot-separated path.

        Args:
            feature_path: e.g. "system1.cache_ttl"
            default: Fallback value if path not found
        """
        return self._get(f"cognitive_features.{feature_path}", default)

    def _get(self, path: str, default: Any = None) -> Any:
        """Navigate nested dict by dot-separated path"""
        keys = path.split(".")
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current


# Singleton instance
feature_flags = FeatureFlags()
