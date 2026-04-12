"""Shared fixtures for LazyVolt integration tests."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Prime the pycares DNS resolver background thread at import time (module level),
# before pytest-homeassistant-custom-component's verify_cleanup fixture captures
# threads_before for any test. pycares._ChannelShutdownManager starts a
# _run_safe_shutdown_loop daemon thread on the first aiohttp session creation;
# if that happens during a test, verify_cleanup flags it as a lingering thread.
_prime_loop = asyncio.new_event_loop()


async def _prime_pycares() -> None:
    async with aiohttp.ClientSession():
        pass


_prime_loop.run_until_complete(_prime_pycares())
_prime_loop.close()

from custom_components.lazyvolt.const import (
    CONF_CLOUD_TOKEN,
    CONF_PEBLAR_ENTRY_ID,
    DOMAIN,
    PEBLAR_DOMAIN,
)


MOCK_CLOUD_URL = "http://localhost:80"
MOCK_TOKEN = "1|mock_token"
MOCK_PEBLAR_ENTRY_ID = "peblar_entry_abc123"


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "cloud_url": MOCK_CLOUD_URL,
            "edge_name": "Home Assistant",
            CONF_CLOUD_TOKEN: MOCK_TOKEN,
            CONF_PEBLAR_ENTRY_ID: MOCK_PEBLAR_ENTRY_ID,
        },
    )


@pytest.fixture
def mock_peblar_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=PEBLAR_DOMAIN,
        title="Peblar EV Charger",
        entry_id=MOCK_PEBLAR_ENTRY_ID,
    )


@pytest.fixture
def mock_api():
    """Mock LazyVoltApiClient."""
    api = MagicMock()
    api.authenticate = AsyncMock(return_value=MOCK_TOKEN)
    api.get_decision = AsyncMock(return_value={"mode": "SOLAR", "phases": 1, "amps": 6})
    api.post_telemetry = AsyncMock(return_value=None)
    api.post_progress = AsyncMock(return_value=None)
    api.token = MOCK_TOKEN
    return api


@pytest.fixture
def mock_entity_ids() -> dict[str, str]:
    """Typical entity IDs for a Peblar device named 'peblar'."""
    return {
        "smart_charging": "select.peblar_smart_charging",
        "cp_state": "sensor.peblar_cp_state",
        "energy_total": "sensor.peblar_energy_total",
        "energy_session": "sensor.peblar_energy_session",
        "power_phase_1": "sensor.peblar_power_phase_1",
        "power_phase_2": "sensor.peblar_power_phase_2",
        "power_phase_3": "sensor.peblar_power_phase_3",
        "current_phase_1": "sensor.peblar_current_phase_1",
        "current_phase_2": "sensor.peblar_current_phase_2",
        "current_phase_3": "sensor.peblar_current_phase_3",
        "charge": "switch.peblar_charge",
        "force_single_phase": "switch.peblar_force_single_phase",
    }
