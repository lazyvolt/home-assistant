"""Tests for LazyVoltCoordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant, ServiceCall, callback

from custom_components.lazyvolt.api import LazyVoltApiError
from custom_components.lazyvolt.coordinator import LazyVoltCoordinator
from tests.conftest import MOCK_PEBLAR_ENTRY_ID


@pytest.fixture
def service_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Register mock select/switch services and return a list of recorded calls."""
    calls: list[ServiceCall] = []

    @callback
    def record(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register("select", "select_option", record)
    hass.services.async_register("switch", "turn_on", record)
    hass.services.async_register("switch", "turn_off", record)
    return calls


def _make_coordinator(hass: HomeAssistant, mock_api, mock_entity_ids) -> LazyVoltCoordinator:
    coordinator = LazyVoltCoordinator(hass, mock_api, MOCK_PEBLAR_ENTRY_ID)
    coordinator._entity_ids = mock_entity_ids
    return coordinator


def _set_states(hass: HomeAssistant, states: dict[str, str]) -> None:
    for entity_id, state_value in states.items():
        hass.states.async_set(entity_id, state_value)


async def test_solar_mode_sets_smart_solar(hass, mock_api, mock_entity_ids, service_calls):
    """SOLAR decision → Peblar smart_charging set to smart_solar."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "SOLAR"})
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)
    _set_states(hass, {
        mock_entity_ids["smart_charging"]: "default",
        mock_entity_ids["charge"]: "on",
        mock_entity_ids["cp_state"]: "charging",
        mock_entity_ids["energy_total"]: "1234.5",
        mock_entity_ids["energy_session"]: "5.0",
    })

    data = await coordinator._async_update_data()

    assert data["mode"] == "SOLAR"
    select_calls = [c for c in service_calls if c.domain == "select"]
    assert any(c.data.get("option") == "smart_solar" for c in select_calls)


async def test_max_mode_sets_default(hass, mock_api, mock_entity_ids, service_calls):
    """MAX decision → Peblar smart_charging set to default."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "MAX"})
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)
    _set_states(hass, {
        mock_entity_ids["smart_charging"]: "smart_solar",
        mock_entity_ids["charge"]: "on",
        mock_entity_ids["cp_state"]: "charging",
        mock_entity_ids["energy_total"]: "1000.0",
        mock_entity_ids["energy_session"]: "2.0",
    })

    await coordinator._async_update_data()

    select_calls = [c for c in service_calls if c.domain == "select"]
    assert any(c.data.get("option") == "default" for c in select_calls)


async def test_standby_turns_off_charger(hass, mock_api, mock_entity_ids, service_calls):
    """STANDBY decision → charge switch turned off."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "STANDBY"})
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)
    _set_states(hass, {
        mock_entity_ids["charge"]: "on",
        mock_entity_ids["cp_state"]: "suspended",
        mock_entity_ids["energy_total"]: "500.0",
        mock_entity_ids["energy_session"]: "0.0",
    })

    await coordinator._async_update_data()

    switch_calls = [c for c in service_calls if c.domain == "switch"]
    assert any(c.service == "turn_off" for c in switch_calls)


async def test_mode_not_reapplied_when_already_set(hass, mock_api, mock_entity_ids, service_calls):
    """Smart charging mode is not re-set when Peblar already has correct mode."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "SOLAR"})
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)
    _set_states(hass, {
        mock_entity_ids["smart_charging"]: "smart_solar",  # already correct
        mock_entity_ids["charge"]: "on",
        mock_entity_ids["cp_state"]: "charging",
        mock_entity_ids["energy_total"]: "1000.0",
        mock_entity_ids["energy_session"]: "3.0",
    })

    await coordinator._async_update_data()

    select_calls = [c for c in service_calls if c.domain == "select"]
    assert len(select_calls) == 0


async def test_progress_posts_lifetime_energy_in_wh(hass, mock_api, mock_entity_ids, service_calls):
    """Lifetime energy (kWh) is converted to Wh and posted to progress endpoint."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "SOLAR"})
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)
    _set_states(hass, {
        mock_entity_ids["smart_charging"]: "smart_solar",
        mock_entity_ids["charge"]: "on",
        mock_entity_ids["cp_state"]: "charging",
        mock_entity_ids["energy_total"]: "12.345",
        mock_entity_ids["energy_session"]: "3.0",
    })

    await coordinator._async_update_data()

    mock_api.post_progress.assert_called_once_with(12345)


async def test_telemetry_maps_cp_state_to_cloud_status(hass, mock_api, mock_entity_ids, service_calls):
    """Peblar no_ev_connected maps to Cloud no_vehicle status."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "STANDBY"})
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)
    _set_states(hass, {
        mock_entity_ids["charge"]: "off",
        mock_entity_ids["cp_state"]: "no_ev_connected",
        mock_entity_ids["energy_total"]: "100.0",
        mock_entity_ids["energy_session"]: "0.0",
    })

    await coordinator._async_update_data()

    call_kwargs = mock_api.post_telemetry.call_args[0][0]
    assert call_kwargs["charger_status"] == "no_vehicle"


async def test_update_fails_gracefully_when_cloud_unreachable(hass, mock_api, mock_entity_ids):
    """UpdateFailed is raised when Cloud decision endpoint is unreachable."""
    from homeassistant.helpers.update_coordinator import UpdateFailed
    mock_api.get_decision = AsyncMock(side_effect=LazyVoltApiError("Cannot connect"))
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_telemetry_failure_does_not_fail_update(hass, mock_api, mock_entity_ids, service_calls):
    """Telemetry POST failure is swallowed — coordinator update succeeds."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "SOLAR"})
    mock_api.post_telemetry = AsyncMock(side_effect=LazyVoltApiError("Telemetry failed"))
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)
    _set_states(hass, {
        mock_entity_ids["smart_charging"]: "smart_solar",
        mock_entity_ids["charge"]: "on",
        mock_entity_ids["cp_state"]: "charging",
        mock_entity_ids["energy_total"]: "50.0",
        mock_entity_ids["energy_session"]: "1.0",
    })

    data = await coordinator._async_update_data()
    assert data["mode"] == "SOLAR"


async def test_single_phase_detected_from_force_single_phase_switch(hass, mock_api, mock_entity_ids, service_calls):
    """force_single_phase switch on → phases reported as 1."""
    mock_api.get_decision = AsyncMock(return_value={"mode": "SOLAR"})
    coordinator = _make_coordinator(hass, mock_api, mock_entity_ids)
    _set_states(hass, {
        mock_entity_ids["smart_charging"]: "smart_solar",
        mock_entity_ids["charge"]: "on",
        mock_entity_ids["cp_state"]: "charging",
        mock_entity_ids["force_single_phase"]: "on",
        mock_entity_ids["energy_total"]: "10.0",
        mock_entity_ids["energy_session"]: "1.0",
    })

    await coordinator._async_update_data()

    call_kwargs = mock_api.post_telemetry.call_args[0][0]
    assert call_kwargs["charger_phases"] == 1
