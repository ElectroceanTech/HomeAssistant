from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up EOT switches from config entry."""
    coordinator = entry.runtime_data.coordinator
    
    switches_data = coordinator.data.get("switches", {})
    
    
    entities = []
    for device_id, device_data in switches_data.items():
        entities.append(
            EotHomeSwitch(
                coordinator=coordinator,
                device_id=device_id,
                device_data=device_data,
                hass=hass,
            )
        )
    
    if entities:
        async_add_entities(entities)


class EotHomeSwitch(EotHomeEntity, SwitchEntity):
    """EOT HOME switch - dynamically created."""

    def __init__(
        self,
        coordinator: EotDataUpdateCoordinator,
        device_id: str,
        device_data: dict[str, Any],
        hass: HomeAssistant,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.hass = hass
        self._device_id = device_id
        self._device_data = device_data
        self.apiClient = coordinator.apiClient
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_id}"

        # Use device name (no entity name)
        self._attr_name = device_data.get("name", f"Switch {device_id}")
        self._attr_has_entity_name = False
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_data.get("name", "Unknown Device"),
            manufacturer=device_data.get("manufacturer", "EOT HOME"),
            model=device_data.get("model", "Switch"),
            sw_version=device_data.get("sw_version"),
            hw_version=device_data.get("hw_version"),
        )
        
    @property
    def is_on(self) -> bool:

        switches = self.coordinator.data.get("switches", {})
        device = switches.get(self._device_id, {})
        state = device.get("state", "off")
        return state == "on"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        switches = self.coordinator.data.get("switches", {})
        device = switches.get(self._device_id, {})
        return device.get("available", True)

    async def async_turn_on(self, **_: Any) -> None:
        """Turn the switch on."""  
        try:
            # Send command to API
            success = await self.apiClient.async_handle_on_off(self._device_id, True)
            
            if success:
                if "switches" in self.coordinator.data:
                    if self._device_id in self.coordinator.data["switches"]:
                        self.coordinator.data["switches"][self._device_id]["state"] = "on"
                        self.async_write_ha_state()

                
        except Exception as e:
            return

    async def async_turn_off(self, **_: Any) -> None:
        """Turn the switch off.""" 
        try:
            success = await self.apiClient.async_handle_on_off(self._device_id, False)
            
            if success:
                if "switches" in self.coordinator.data:
                    if self._device_id in self.coordinator.data["switches"]:
                        self.coordinator.data["switches"][self._device_id]["state"] = "off"
                        self.async_write_ha_state()
                
        except Exception as e:
            return

    async def async_update(self) -> None:
        """Update the entity.
        
        This is called by the coordinator when data is refreshed.
        """        
        self.async_write_ha_state()