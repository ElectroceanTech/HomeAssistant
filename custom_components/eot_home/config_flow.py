"""Adds config flow for EOT HOME."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from slugify import slugify

from .api import (
    EotHomeApiClient,
    EotHomeApiClientAuthenticationError,
    EotHomeApiClientCommunicationError,
    EotHomeApiClientError,
)
from .auth import EOTAuthHandler
from .const import DOMAIN, LOGGER


class EotFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EOT HOME."""
    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    #entry.data[CONF_USERNAME]
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    
                )
            except EotHomeApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except EotHomeApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except EotHomeApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                                        unique_id=slugify(user_input[CONF_USERNAME])
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.EMAIL,
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    async def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        session = async_create_clientsession(self.hass)
        
        auth_handler = EOTAuthHandler(
            session=session,
            username=username,
            password=password,
        )
        
        if not await auth_handler.async_validate_auth():
            raise EotHomeApiClientAuthenticationError(
                "Invalid credentials"
            )
        
        client = EotHomeApiClient(
            session=session,
            auth_handler=auth_handler,
            user_email=username
            )
        
        try:
            await client.async_get_data()
        except Exception as err:
            LOGGER.warning(
                "API test failed (this is OK if endpoint not implemented yet): %s",
                err
            )
            pass