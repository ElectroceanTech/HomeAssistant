from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    ATTR_POSITION,
)
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
    """Set up EOT covers from config entry."""
    coordinator = entry.runtime_data.coordinator
    
    covers_data = coordinator.data.get("covers", {})
    
    
    entities = []
    for device_id, device_data in covers_data.items():
        entities.append(
            EotHomeCover(
                coordinator=coordinator,
                device_id=device_id,
                device_data=device_data,
                hass=hass,
            )
        )
    
    if entities:
        async_add_entities(entities)


class EotHomeCover(EotHomeEntity, CoverEntity):
    """EOT HOME curtain cover - dynamically created."""
    

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
    )

    def __init__(
        self,
        coordinator: EotDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
        hass: HomeAssistant,
    ) -> None:
        """Initialize the cover."""
        super().__init__(coordinator)
        self.hass = hass
        self._device_id = device_id
        self._device_data = device_data
        self.apiClient = coordinator.apiClient
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_id}"
        self._attr_name = device_data.get("name", f"Cover {device_id}")
        self._attr_has_entity_name = False
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data.get("name", "Unknown Cover"),
            manufacturer=device_data.get("manufacturer", "EOT HOME"),
            model=device_data.get("model", "Curtain"),
            sw_version=device_data.get("sw_version"),
        )
        

    @property
    def current_cover_position(self) -> int:
        """Return current position from coordinator data."""
        covers = self.coordinator.data.get("covers", {})
        device = covers.get(self._device_id, {})
        
        position = device.get("position", 0)
                
        return position

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed from coordinator data."""
        covers = self.coordinator.data.get("covers", {})
        device = covers.get(self._device_id, {})
        
        # Check if position is 0 or if there's an explicit is_closed field
        position = device.get("position", 0)
        is_closed = device.get("is_closed", position == 0)
                
        return is_closed

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        covers = self.coordinator.data.get("covers", {})
        device = covers.get(self._device_id, {})
        return device.get("available", True)

    async def async_open_cover(self, **_: Any) -> None:
        """Open the cover."""
        
        try:
            success = await self.apiClient.async_handle_curtain_position(self._device_id, 100)
            
            if success:

                if "covers" in self.coordinator.data:
                    if self._device_id in self.coordinator.data["covers"]:
                        self.coordinator.data["covers"][self._device_id]["position"] = 100
                        self.coordinator.data["covers"][self._device_id]["is_closed"] = False
                        self.async_write_ha_state()

                
        except Exception as e:
            return

    async def async_close_cover(self, **_: Any) -> None:
        """Close the cover."""
        
        try:
            success = await self.apiClient.async_handle_curtain_position(self._device_id, 0)
            
            if success:

                if "covers" in self.coordinator.data:
                    if self._device_id in self.coordinator.data["covers"]:
                        self.coordinator.data["covers"][self._device_id]["position"] = 0
                        self.coordinator.data["covers"][self._device_id]["is_closed"] = True
                        self.async_write_ha_state()
           
                
        except Exception as e:
            return

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION, 0)
        
        try:

            if position < 50:
                position = 0
            else:
                position = 100
            
            success = await self.apiClient.async_handle_curtain_position(self._device_id, position)
            
            if success:
                if "covers" in self.coordinator.data:
                    if self._device_id in self.coordinator.data["covers"]:
                        self.coordinator.data["covers"][self._device_id]["position"] = position
                        self.coordinator.data["covers"][self._device_id]["is_closed"] = position == 0
                        self.async_write_ha_state()
                
        except Exception as e:
            return

    async def async_stop_cover(self, **_: Any) -> None:
        """Stop the cover """
        covers = self.coordinator.data.get("covers", {})
        device = covers.get(self._device_id, {})
        current_position = device.get("position", 0)
        
        try:
            success = await self.apiClient.async_handle_curtain_position(
                self._device_id, 
                current_position
            )
            
        except Exception as e:
            return

    async def async_update(self) -> None:
        """Update the entity.
        
        This is called by the coordinator when data is refreshed.
        """
        self.async_write_ha_state()