from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
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
    """Set up EOT motion sensors from config entry."""
    coordinator = entry.runtime_data.coordinator
    
    motion_sensors_data = coordinator.data.get("motion_sensors", {})
    
    entities = []
    for device_id, device_data in motion_sensors_data.items():
        entities.append(
            EotHomeMotionSensor(
                coordinator=coordinator,
                device_id=device_id,
                device_data=device_data,
                hass=hass,
            )
        )
    
    if entities:
        async_add_entities(entities)


class EotHomeMotionSensor(EotHomeEntity, BinarySensorEntity):
    """EOT Home motion sensor - dynamically created."""

    def __init__(
        self,
        coordinator: EotDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
        hass: HomeAssistant,
    ) -> None:
        """Initialize the motion sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self._device_id = device_id
        self._device_data = device_data
        self.apiClient = coordinator.apiClient
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_id}"

        # Use device name (no entity name)
        self._attr_name = device_data.get("name", f"Motion Sensor {device_id}")
        self._attr_has_entity_name = False
        
        # Set device class to motion for proper icon and representation
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data.get("name", "Unknown Motion Sensor"),
            manufacturer=device_data.get("manufacturer", "EOT Home"),
            model=device_data.get("model", "Motion Sensor"),
            sw_version=device_data.get("sw_version"),
            hw_version=device_data.get("hw_version"),
        )
    
    @property
    def is_on(self) -> bool:
        """Return True if motion is detected."""
        motion_sensors = self.coordinator.data.get("motion_sensors", {})
        device = motion_sensors.get(self._device_id, {})
        state = device.get("state", "not_detected")
        # state can be "detected" or "not_detected"
        return state == "detected"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        motion_sensors = self.coordinator.data.get("motion_sensors", {})
        device = motion_sensors.get(self._device_id, {})
        return device.get("available", True)

    async def async_update(self) -> None:
        """Update the entity.
        
        This is called by the coordinator when data is refreshed.
        Motion sensors are read-only, so no turn_on/turn_off methods needed.
        """
        self.async_write_ha_state()