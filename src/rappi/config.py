"""Configuration management — persists token, deviceId, and coordinates to ~/.rappi/config.json."""

import json
import os
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from rappi.constants import DEFAULT_LAT, DEFAULT_LNG

CONFIG_DIR = Path.home() / ".rappi"
CONFIG_FILE = CONFIG_DIR / "config.json"


class RecentOrder(BaseModel):
    store_id: int
    store_name: str
    product_names: list[str] = []
    timestamp: str = ""  # ISO format


class RappiConfig(BaseModel):
    token: str | None = None
    device_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lat: float = DEFAULT_LAT
    lng: float = DEFAULT_LNG
    active_address_id: int | None = None
    recent_orders: list[RecentOrder] = []
    favorite_store_ids: list[int] = []


class ConfigManager:
    def __init__(self, path: Path = CONFIG_FILE):
        self._path = path

    def load(self) -> RappiConfig:
        if self._path.exists():
            data = json.loads(self._path.read_text())
            config = RappiConfig(**data)
        else:
            config = RappiConfig()
        # Environment variables override file config (for remote deployment)
        env_token = os.environ.get("RAPPI_TOKEN")
        if env_token:
            config.token = env_token
        env_device_id = os.environ.get("RAPPI_DEVICE_ID")
        if env_device_id:
            config.device_id = env_device_id
        env_lat = os.environ.get("RAPPI_LAT")
        env_lng = os.environ.get("RAPPI_LNG")
        if env_lat:
            config.lat = float(env_lat)
        if env_lng:
            config.lng = float(env_lng)
        return config

    def save(self, config: RappiConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(config.model_dump_json(indent=2))

    def update(self, **kwargs) -> RappiConfig:
        """Load, update fields, save, and return the updated config."""
        config = self.load()
        for key, value in kwargs.items():
            setattr(config, key, value)
        self.save(config)
        return config
