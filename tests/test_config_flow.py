"""Tests for the LazyVolt config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lazyvolt.api import LazyVoltApiError, LazyVoltAuthError
from custom_components.lazyvolt.const import (
    CONF_CLOUD_TOKEN,
    CONF_PEBLAR_ENTRY_ID,
    DOMAIN,
    PEBLAR_DOMAIN,
    PRODUCTION_CLOUD_URL,
)
from tests.conftest import MOCK_CLOUD_URL, MOCK_PEBLAR_ENTRY_ID, MOCK_TOKEN


async def test_user_step_success_single_peblar_dev_mode(hass, mock_peblar_entry):
    """Dev mode: URL field shown; auth succeeds, single Peblar → entry created."""
    mock_peblar_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", True), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value=MOCK_TOKEN,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "cloud_url": MOCK_CLOUD_URL,
                "edge_name": "Home Assistant",
                "email": "user@example.com",
                "password": "secret",
            },
        )

    assert result["type"] == "create_entry"
    assert result["data"]["cloud_url"] == MOCK_CLOUD_URL
    assert result["data"][CONF_CLOUD_TOKEN] == MOCK_TOKEN
    assert result["data"][CONF_PEBLAR_ENTRY_ID] == MOCK_PEBLAR_ENTRY_ID


async def test_user_step_success_single_peblar_production(hass, mock_peblar_entry):
    """Production mode: no URL field; cloud URL hardcoded to production URL."""
    mock_peblar_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value=MOCK_TOKEN,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "Home Assistant", "email": "user@example.com", "password": "secret"},
        )

    assert result["type"] == "create_entry"
    assert result["data"]["cloud_url"] == PRODUCTION_CLOUD_URL
    assert result["data"][CONF_CLOUD_TOKEN] == MOCK_TOKEN


async def test_user_step_multiple_peblar_shows_selection(hass):
    """Multiple Peblar entries → peblar selection step is shown."""
    entry_a = MockConfigEntry(domain=PEBLAR_DOMAIN, title="Charger A", entry_id="entry_a")
    entry_b = MockConfigEntry(domain=PEBLAR_DOMAIN, title="Charger B", entry_id="entry_b")
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value=MOCK_TOKEN,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "HA", "email": "u@e.com", "password": "p"},
        )

    assert result["type"] == "form"
    assert result["step_id"] == "peblar"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PEBLAR_ENTRY_ID: "entry_b"}
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_PEBLAR_ENTRY_ID] == "entry_b"


async def test_user_step_invalid_auth_shows_error(hass, mock_peblar_entry):
    """Wrong credentials show an error, form is re-displayed."""
    mock_peblar_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        side_effect=LazyVoltAuthError("Invalid credentials"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "HA", "email": "bad@e.com", "password": "wrong"},
        )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_auth"


async def test_user_step_cannot_connect_shows_error(hass, mock_peblar_entry):
    """Connection failure shows an error."""
    mock_peblar_entry.add_to_hass(hass)

    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        side_effect=LazyVoltApiError("Cannot connect"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "HA", "email": "u@e.com", "password": "p"},
        )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"


async def test_no_peblar_aborts_flow(hass):
    """No Peblar integration installed → flow aborts with reason."""
    with patch("custom_components.lazyvolt.config_flow._DEV_MODE", False), patch(
        "custom_components.lazyvolt.config_flow.LazyVoltApiClient.authenticate",
        new_callable=AsyncMock,
        return_value=MOCK_TOKEN,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"edge_name": "HA", "email": "u@e.com", "password": "p"},
        )

    assert result["type"] == "abort"
    assert result["reason"] == "no_peblar"
