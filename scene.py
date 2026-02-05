from __future__ import annotations

from typing import TYPE_CHECKING, Any
import aiohttp

from homeassistant.components.scene import Scene
from homeassistant.helpers.device_registry import DeviceInfo

from .entity import EotHomeEntity
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from .coordinator import EotDataUpdateCoordinator
    from .data import EotHomeConfigEntry




async def async_setup_entry(
    hass: HomeAssistant,
    entry: EotHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EOT scenes from config entry."""
    coordinator = entry.runtime_data.coordinator
    
    scenes_data = coordinator.data.get("scenes", {})
    
    
    entities = []
    for device_id, device_data in scenes_data.items():
        entities.append(
            EotHomeScene(
                coordinator=coordinator,
                device_id=device_id,
                device_data=device_data,
                hass=hass,
            )
        )
    
    if entities:
        async_add_entities(entities)


class EotHomeScene(EotHomeEntity, Scene):
    """EOT Home scene - dynamically created."""

    def __init__(
        self,
        coordinator: EotDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
        hass: HomeAssistant,
    ) -> None:
        """Initialize the scene."""
        super().__init__(coordinator)
        self.hass = hass
        self._device_id = device_id
        self._device_data = device_data
        self.apiClient = coordinator.apiClient
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_id}"
        self._attr_name = device_data.get("name", f"Scene {device_id}")
        self._attr_has_entity_name = False
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data.get("name", "Unknown Scene"),
            manufacturer=device_data.get("manufacturer", "EOT Home"),
            model=device_data.get("model", "Scene"),
            sw_version=device_data.get("sw_version"),
        )

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        await self.apiClient.async_handle_scene(self._device_id)
        
