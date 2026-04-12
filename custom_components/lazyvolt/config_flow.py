"""Config flow for the LazyVolt integration."""
from __future__ import annotations

import os

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import LazyVoltApiClient, LazyVoltApiError, LazyVoltAuthError
from .const import (
    CONF_CLOUD_TOKEN,
    CONF_PEBLAR_ENTRY_ID,
    DEFAULT_CLOUD_URL,
    DEFAULT_EDGE_NAME,
    DOMAIN,
    PEBLAR_DOMAIN,
    PRODUCTION_CLOUD_URL,
)

_DEV_MODE = bool(os.environ.get("LAZYVOLT_DEV"))


class LazyVoltConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step config flow: Cloud auth → Peblar device selection."""

    VERSION = 1

    def __init__(self) -> None:
        self._cloud_url: str = DEFAULT_CLOUD_URL
        self._edge_name: str = DEFAULT_EDGE_NAME
        self._token: str = ""

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            cloud_url = user_input.get("cloud_url", PRODUCTION_CLOUD_URL)
            session = aiohttp_client.async_get_clientsession(self.hass)
            api = LazyVoltApiClient(cloud_url, session)
            try:
                token = await api.authenticate(
                    user_input["email"],
                    user_input["password"],
                    user_input["edge_name"],
                )
            except LazyVoltAuthError:
                errors["base"] = "invalid_auth"
            except LazyVoltApiError:
                errors["base"] = "cannot_connect"
            else:
                self._cloud_url = cloud_url
                self._edge_name = user_input["edge_name"]
                self._token = token
                return await self.async_step_peblar()

        fields: dict = {
            vol.Required("edge_name", default=DEFAULT_EDGE_NAME): str,
            vol.Required("email"): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL)
            ),
            vol.Required("password"): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
        if _DEV_MODE:
            fields = {
                vol.Required("cloud_url", default=DEFAULT_CLOUD_URL): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
                **fields,
            }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(fields),
            errors=errors,
        )

    async def async_step_peblar(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        peblar_entries = [
            e for e in self.hass.config_entries.async_entries(PEBLAR_DOMAIN)
        ]

        if not peblar_entries:
            return self.async_abort(reason="no_peblar")

        if user_input is not None:
            return self.async_create_entry(
                title=f"LazyVolt ({self._edge_name})",
                data={
                    "cloud_url": self._cloud_url,
                    "edge_name": self._edge_name,
                    CONF_CLOUD_TOKEN: self._token,
                    CONF_PEBLAR_ENTRY_ID: user_input[CONF_PEBLAR_ENTRY_ID],
                },
            )

        # Auto-advance if exactly one Peblar device is configured
        if len(peblar_entries) == 1:
            return self.async_create_entry(
                title=f"LazyVolt ({self._edge_name})",
                data={
                    "cloud_url": self._cloud_url,
                    "edge_name": self._edge_name,
                    CONF_CLOUD_TOKEN: self._token,
                    CONF_PEBLAR_ENTRY_ID: peblar_entries[0].entry_id,
                },
            )

        options = [
            SelectOptionDict(value=e.entry_id, label=e.title) for e in peblar_entries
        ]

        return self.async_show_form(
            step_id="peblar",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PEBLAR_ENTRY_ID): SelectSelector(
                        SelectSelectorConfig(options=options)
                    ),
                }
            ),
        )
