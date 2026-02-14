"""
Unit tests for feature flags system.
Tests config loading, defaults, deep merge, and flag queries.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.feature_flags import FeatureFlags, _DEFAULT_CONFIG


class TestFeatureFlagsDefaults:
    """Test default configuration when no YAML file exists."""

    def test_all_disabled_by_default(self):
        """Master switch and all features should be disabled by default."""
        flags = FeatureFlags(config_path=Path("/nonexistent/path.yaml"))
        assert flags.enabled is False

    def test_is_enabled_returns_false_when_master_off(self):
        """No feature should be enabled when master switch is off."""
        flags = FeatureFlags(config_path=Path("/nonexistent/path.yaml"))
        assert flags.is_enabled("system1.enable_cache") is False
        assert flags.is_enabled("system2.enable_thinking_chain") is False
        assert flags.is_enabled("routing.smart_routing") is False
        assert flags.is_enabled("metrics.cognitive_metrics") is False

    def test_get_value_returns_defaults(self):
        """get_value should return default config values."""
        flags = FeatureFlags(config_path=Path("/nonexistent/path.yaml"))
        assert flags.get_value("system1.cache_ttl") == 300
        assert flags.get_value("system1.cache_max_size") == 1000
        assert flags.get_value("system2.max_thinking_time") == 30
        assert flags.get_value("system2.reflection_depth") == 3

    def test_get_value_with_fallback(self):
        """get_value should return fallback for nonexistent paths."""
        flags = FeatureFlags(config_path=Path("/nonexistent/path.yaml"))
        assert flags.get_value("nonexistent.path", "fallback") == "fallback"
        assert flags.get_value("system1.nonexistent", 42) == 42


class TestFeatureFlagsYAMLLoading:
    """Test loading from actual YAML files."""

    def test_load_from_project_yaml(self):
        """Load from the project's cognitive_features.yaml."""
        project_config = Path(__file__).parent.parent.parent / "config" / "cognitive_features.yaml"
        if project_config.exists():
            flags = FeatureFlags(config_path=project_config)
            # Project config has all flags false
            assert flags.enabled is False

    def test_load_with_overrides(self):
        """YAML overrides should merge with defaults."""
        yaml_content = """
cognitive_features:
  enabled: true
  system1:
    enable_cache: true
    cache_ttl: 600
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            flags = FeatureFlags(config_path=Path(f.name))

        assert flags.enabled is True
        assert flags.is_enabled("system1.enable_cache") is True
        assert flags.get_value("system1.cache_ttl") == 600
        # Unoverridden values should keep defaults
        assert flags.get_value("system1.cache_max_size") == 1000
        assert flags.get_value("system2.max_thinking_time") == 30

    def test_master_switch_gates_features(self):
        """Features enabled in config but master off should return False."""
        yaml_content = """
cognitive_features:
  enabled: false
  system1:
    enable_cache: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            flags = FeatureFlags(config_path=Path(f.name))

        assert flags.enabled is False
        assert flags.is_enabled("system1.enable_cache") is False


class TestDeepMerge:
    """Test the deep merge utility."""

    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = FeatureFlags._deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}
        result = FeatureFlags._deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 100}, "b": 3}

    def test_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        override = {"a": {"x": 2}}
        FeatureFlags._deep_merge(base, override)
        assert base["a"]["x"] == 1


class TestFeatureFlagsSingleton:
    """Test the module-level singleton instance."""

    def test_singleton_exists(self):
        from core.feature_flags import feature_flags
        assert feature_flags is not None
        assert isinstance(feature_flags, FeatureFlags)

    def test_singleton_defaults_safe(self):
        from core.feature_flags import feature_flags
        # Singleton should have safe defaults (all off)
        assert feature_flags.is_enabled("system1.enable_cache") is False
        assert feature_flags.is_enabled("routing.smart_routing") is False
