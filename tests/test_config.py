"""Tests for rappi.config — ConfigManager and RappiConfig model."""

import json
from pathlib import Path

import pytest

from rappi.config import ConfigManager, RappiConfig, RecentOrder


class TestRappiConfig:
    def test_default_values(self):
        cfg = RappiConfig()
        assert cfg.token is None
        assert cfg.device_id  # auto-generated UUID
        assert cfg.lat == pytest.approx(4.624335)
        assert cfg.lng == pytest.approx(-74.063644)
        assert cfg.active_address_id is None
        assert cfg.recent_orders == []
        assert cfg.favorite_store_ids == []

    def test_device_id_is_unique(self):
        cfg1 = RappiConfig()
        cfg2 = RappiConfig()
        assert cfg1.device_id != cfg2.device_id

    def test_with_token(self):
        cfg = RappiConfig(token="my-token")
        assert cfg.token == "my-token"


class TestRecentOrder:
    def test_creation(self):
        order = RecentOrder(store_id=123, store_name="Test Store", product_names=["Pizza"])
        assert order.store_id == 123
        assert order.store_name == "Test Store"
        assert order.product_names == ["Pizza"]
        assert order.timestamp == ""


class TestConfigManager:
    def test_load_missing_file(self, tmp_config):
        cm, config_file = tmp_config
        cfg = cm.load()
        assert isinstance(cfg, RappiConfig)
        assert cfg.token is None

    def test_save_and_load(self, tmp_config):
        cm, config_file = tmp_config
        original = RappiConfig(token="test-token", lat=10.0, lng=-75.0)
        cm.save(original)

        assert config_file.exists()
        loaded = cm.load()
        assert loaded.token == "test-token"
        assert loaded.lat == pytest.approx(10.0)
        assert loaded.lng == pytest.approx(-75.0)

    def test_save_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "config.json"
        cm = ConfigManager(path=nested)
        cm.save(RappiConfig(token="t"))
        assert nested.exists()

    def test_update(self, tmp_config):
        cm, _ = tmp_config
        cm.save(RappiConfig(token="old-token"))

        updated = cm.update(token="new-token", lat=5.0)
        assert updated.token == "new-token"
        assert updated.lat == pytest.approx(5.0)

        # Persisted to disk
        reloaded = cm.load()
        assert reloaded.token == "new-token"

    def test_update_preserves_existing_fields(self, tmp_config):
        cm, _ = tmp_config
        cm.save(RappiConfig(token="keep-me", device_id="my-device"))

        updated = cm.update(lat=99.0)
        assert updated.token == "keep-me"
        assert updated.device_id == "my-device"
        assert updated.lat == pytest.approx(99.0)

    def test_saved_file_is_valid_json(self, tmp_config):
        cm, config_file = tmp_config
        cm.save(RappiConfig(token="t"))
        data = json.loads(config_file.read_text())
        assert "token" in data
        assert data["token"] == "t"

    def test_favorite_store_ids_round_trip(self, tmp_config):
        cm, _ = tmp_config
        cm.save(RappiConfig(favorite_store_ids=[100, 200, 300]))
        loaded = cm.load()
        assert loaded.favorite_store_ids == [100, 200, 300]
