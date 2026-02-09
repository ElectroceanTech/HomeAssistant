"""Custom types for eot_home."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import EotHomeApiClient
    from .coordinator import EotDataUpdateCoordinator


type EotHomeConfigEntry = ConfigEntry[EotHomeData]


@dataclass
class EotHomeData:
    """Data for the EOT integration."""

    client: EotHomeApiClient
    coordinator: EotDataUpdateCoordinator
    integration: Integration
