"""DataUpdateCoordinator for eot_home."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    EotHomeApiClient,
    EotHomeApiClientAuthenticationError,
    EotHomeApiClientError,
    DeviceConverter,
)
from .const import LOGGER

if TYPE_CHECKING:
    from datetime import timedelta
    from homeassistant.core import HomeAssistant


class EotDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        apiClient: EotHomeApiClient,
        logger,
        name: str,
        update_interval: timedelta | None, 
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=logger,
            name=name,
            update_interval=update_interval,  
        )
        self.apiClient = apiClient

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Update data via library - organize devices by Home Assistant type."""
        try:
            devices = await self.apiClient.async_get_devices()
            
            organized_data = {
                "switches": {},
                "lights": {},
                "fans": {},
                "covers": {},
                "scenes": {},
                "motion_sensors": {},  # Changed from binary_sensors to motion_sensors
                "sensors": {},
            }
            
            for device in devices:
                device_id = device.get("id")
                device_type = device.get("type", "switch")  
                capabilities = device.get("capabilities", [])

                cached_state = self.apiClient.get_cached_device_state(device_id)
                if cached_state:
                    ha_state = DeviceConverter.convert_ga_state_to_ha(
                        cached_state,
                        device_type
                    )
                    device.update(ha_state)
                
                # Route devices to appropriate categories
                if device_type == "light":
                    organized_data["lights"][device_id] = device
                elif device_type == "switch":
                    organized_data["switches"][device_id] = device
                elif device_type == "fan":
                    organized_data["fans"][device_id] = device
                elif device_type == "cover":
                    organized_data["covers"][device_id] = device
                elif device_type == "scene":
                    organized_data["scenes"][device_id] = device
                elif device_type == "binary_sensor":
                    # Check if it's a motion sensor specifically
                    if "occupancy" in capabilities:
                        organized_data["motion_sensors"][device_id] = device
                    else:
                        # Other binary sensors can go here
                        organized_data["sensors"][device_id] = device
                else:
                    # Default fallback
                    organized_data["switches"][device_id] = device
            
            return organized_data
            
        except EotHomeApiClientAuthenticationError as exception:
            LOGGER.error("Authentication error: %s", exception)
            raise ConfigEntryAuthFailed(exception) from exception
        except EotHomeApiClientError as exception:
            LOGGER.error("API error: %s", exception)
            raise UpdateFailed(exception) from exception
        except Exception as exception:
            LOGGER.exception("Unexpected error fetching data")
            raise UpdateFailed(f"Unexpected error: {exception}") from exception