from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import math

from homeassistant.components.light import (
    LightEntity,
    ColorMode,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
)
from homeassistant.util.color import value_to_brightness, brightness_to_value
from homeassistant.helpers.device_registry import DeviceInfo

from .entity import EotHomeEntity
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from .coordinator import EotDataUpdateCoordinator
    from .data import EotHomeConfigEntry


BRIGHTNESS_SCALE = (1, 100)
COLOR_TEMP_KELVIN_MIN = 2500
COLOR_TEMP_KELVIN_MAX = 5000


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EotHomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EOT lights from config entry."""
    coordinator = entry.runtime_data.coordinator
    
    lights_data = coordinator.data.get("lights", {})
    entities = []
    for device_id, device_data in lights_data.items():
        entities.append(
            EotHomeLight(
                coordinator=coordinator,
                device_id=device_id,
                device_data=device_data,
                hass=hass,
            )
        )
    
    if entities:
        async_add_entities(entities)


class EotHomeLight(EotHomeEntity, LightEntity):
    """EOT HOME dimmer light - dynamically created."""

    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = COLOR_TEMP_KELVIN_MIN
    _attr_max_color_temp_kelvin = COLOR_TEMP_KELVIN_MAX

    def __init__(
        self,
        coordinator: EotDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
        hass: HomeAssistant,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self.hass = hass
        self._device_id = device_id
        self._device_data = device_data
        self.apiClient = coordinator.apiClient

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_id}"
        self._attr_name = device_data.get("name", f"Light {device_id}")
        self._attr_has_entity_name = False
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data.get("name", "Unknown Light"),
            manufacturer=device_data.get("manufacturer", "EOT HOME"),
            model=device_data.get("model", "Dimmer"),
            sw_version=device_data.get("sw_version"),
        )
        

    @property
    def is_on(self) -> bool:
        """Return current state from coordinator data."""
        lights = self.coordinator.data.get("lights", {})
        device = lights.get(self._device_id, {})
        
        state = device.get("state", "off")
        
        
        return state == "on"

    @property
    def brightness(self) -> Optional[int]:
        """Return the current brightness from coordinator data."""
        lights = self.coordinator.data.get("lights", {})
        device = lights.get(self._device_id, {})
        
        brightness_value = device.get("brightness", 100)
        
        return value_to_brightness(BRIGHTNESS_SCALE, brightness_value)

    @property
    def color_temp_kelvin(self) -> Optional[int]:
        """Return the current color temperature in Kelvin from coordinator data."""
        lights = self.coordinator.data.get("lights", {})
        device = lights.get(self._device_id, {})
        return device.get("color_temp", 3000)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        lights = self.coordinator.data.get("lights", {})
        device = lights.get(self._device_id, {})
        return device.get("available", True)


    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn device on."""
        
        try:
            if ATTR_BRIGHTNESS in kwargs:
                value_in_range = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS]))
                
                success = await self.apiClient.async_handle_brightness(self._device_id, value_in_range)
                
                if success:
                    if "lights" in self.coordinator.data:
                        if self._device_id in self.coordinator.data["lights"]:
                            self.coordinator.data["lights"][self._device_id]["brightness"] = value_in_range
                            self.coordinator.data["lights"][self._device_id]["state"] = "on"
                            self.async_write_ha_state()

                return
                
            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
                success = await self.apiClient.async_handle_color_temp(self._device_id, color_temp)
                
                if success:

                    if "lights" in self.coordinator.data:
                        if self._device_id in self.coordinator.data["lights"]:
                            self.coordinator.data["lights"][self._device_id]["color_temp"] = color_temp
                            self.coordinator.data["lights"][self._device_id]["state"] = "on"
                            self.async_write_ha_state()
                return

            success = await  self.apiClient.async_handle_on_off(self._device_id, True)
            
            if success:

                if "lights" in self.coordinator.data:
                    if self._device_id in self.coordinator.data["lights"]:
                        self.coordinator.data["lights"][self._device_id]["state"] = "on"
                        self.async_write_ha_state()
        except Exception as e:
           return

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn device off."""
        try:
            success = await self.apiClient.async_handle_on_off(self._device_id, False)
            
            if success:

                if "lights" in self.coordinator.data:
                    if self._device_id in self.coordinator.data["lights"]:
                        self.coordinator.data["lights"][self._device_id]["state"] = "off"
                        self.async_write_ha_state() 
        except Exception as e:
            return

    async def async_update(self) -> None:
        """Update the entity.
        
        This is called by the coordinator when data is refreshed.
        """
        self.async_write_ha_state()