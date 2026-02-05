from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
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
    """Set up EOT fans from config entry."""
    coordinator = entry.runtime_data.coordinator
    
    fans_data = coordinator.data.get("fans", {})
    
    
    entities = []
    for device_id, device_data in fans_data.items():
        entities.append(
            EotHomeFan(
                coordinator=coordinator,
                device_id=device_id,
                device_data=device_data,
                hass=hass,
            )
        )
    
    if entities:
        async_add_entities(entities)


class EotHomeFan(EotHomeEntity, FanEntity):
    """EOT Home fan - dynamically created."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | 
        FanEntityFeature.TURN_ON | 
        FanEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        coordinator: EotDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
        hass: HomeAssistant,
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator)
        self.hass = hass
        self._device_id = device_id
        self._device_data = device_data
        self.apiClient = coordinator.apiClient
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_id}"
        self._attr_name = device_data.get("name", f"Fan {device_id}")
        self._attr_has_entity_name = False
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data.get("name", "Unknown Fan"),
            manufacturer=device_data.get("manufacturer", "EOT Home"),
            model=device_data.get("model", "Fan"),
            sw_version=device_data.get("sw_version"),
        )
        
        self._speed_range = (1, 4)
        

    @property
    def is_on(self) -> bool:
        """Return current state from coordinator data."""
        fans = self.coordinator.data.get("fans", {})
        device = fans.get(self._device_id, {})
        
        # Check the state field
        state = device.get("state", "off")
        
        
        return state == "on"

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage from coordinator data."""
        fans = self.coordinator.data.get("fans", {})
        device = fans.get(self._device_id, {})

        speed = device.get("percentage", 0)
        percentage = speed 
        
        return percentage

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return int(self._speed_range[1] - self._speed_range[0] + 1)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        fans = self.coordinator.data.get("fans", {})
        device = fans.get(self._device_id, {})
        return device.get("available", True)

        
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        
        try:
            if percentage is not None:
                await self.async_set_percentage(percentage)
            else:
                success =await self.apiClient.async_handle_on_off(self._device_id, True)
                
                if success:

                    if "fans" in self.coordinator.data:
                        if self._device_id in self.coordinator.data["fans"]:
                            self.coordinator.data["fans"][self._device_id]["state"] = "on"
                            self.async_write_ha_state()

                    
        except Exception as e:
            return

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the fan."""
        try:
            success = await self.apiClient.async_handle_on_off(self._device_id, False)
            if success:

                if "fans" in self.coordinator.data:
                    if self._device_id in self.coordinator.data["fans"]:
                        self.coordinator.data["fans"][self._device_id]["state"] = "off"
                        self.async_write_ha_state()

                
        except Exception as e:
            return

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        
        try:
            if percentage == 0:
                await self.apiClient.async_handle_on_off(self._device_id, False)
            else:
                speed = min(4, ((percentage - 1) // 25) + 1) 
                
                success = await self.apiClient.async_set_speed(self._device_id, speed)
                
                if success:
                    if "fans" in self.coordinator.data:
                        if self._device_id in self.coordinator.data["fans"]:
                            self.coordinator.data["fans"][self._device_id]["percentage"] = percentage
                            self.coordinator.data["fans"][self._device_id]["state"] = "on"
                            self.async_write_ha_state()

                    
        except Exception as e:
            return

    async def async_update(self) -> None:
        """Update the entity.
        
        This is called by the coordinator when data is refreshed.
        """
        self.async_write_ha_state()