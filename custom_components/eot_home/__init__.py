"""
Custom integration to integrate eot_home with Home Assistant.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import EotHomeApiClient
from .auth import EOTAuthHandler
from .const import DOMAIN, LOGGER
from .coordinator import EotDataUpdateCoordinator
from .data import EotHomeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .data import EotHomeConfigEntry

# -------------------------------------------------
# Constants
# -------------------------------------------------

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.FAN,
    Platform.COVER,
    Platform.SCENE,
    Platform.BINARY_SENSOR,
]




async def async_setup_entry(
    hass: HomeAssistant,
    entry: EotHomeConfigEntry,
) -> bool:
    """Set up EOT HOME from a config entry."""

    session = async_get_clientsession(hass)
    
    auth_handler = EOTAuthHandler(
        session=session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        if not await auth_handler.async_validate_auth():
            raise ConfigEntryAuthFailed("Authentication failed")
    except Exception as err:
        LOGGER.exception("Authentication error")
        raise ConfigEntryAuthFailed from err

    api_client = EotHomeApiClient(
        session=session,
        auth_handler=auth_handler,
        user_email=entry.data[CONF_USERNAME],
        entry_id=entry.entry_id,
    )


    coordinator = EotDataUpdateCoordinator(
        hass=hass,
        apiClient=api_client,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(hours=1),
    )


    api_client.set_hass_and_coordinator(hass, coordinator)

    await hass.async_add_executor_job(api_client.start_mqtt)

    entry.runtime_data = EotHomeData(
        client=api_client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    LOGGER.info("EOT HOME integration setup completed")
    return True



async def async_unload_entry(
    hass: HomeAssistant,
    entry: EotHomeConfigEntry,
) -> bool:
    """Unload EOT HOME integration."""

    LOGGER.info("Unloading EOT HOME integration")

    api_client = entry.runtime_data.client

    await hass.async_add_executor_job(api_client.stop_mqtt)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# -------------------------------------------------
# Reload
# -------------------------------------------------

async def async_reload_entry(
    hass: HomeAssistant,
    entry: EotHomeConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
