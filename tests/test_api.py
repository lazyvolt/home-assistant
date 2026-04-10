"""Tests for LazyVoltApiClient."""
from __future__ import annotations

import pytest
import aiohttp
from aioresponses import aioresponses

from custom_components.lazyvolt.api import (
    LazyVoltApiClient,
    LazyVoltApiError,
    LazyVoltAuthError,
)


CLOUD_URL = "http://localhost:80"


@pytest.fixture
def client(hass):
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    session = async_get_clientsession(hass)
    return LazyVoltApiClient(CLOUD_URL, session)


@pytest.fixture
def authed_client(hass):
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    session = async_get_clientsession(hass)
    return LazyVoltApiClient(CLOUD_URL, session, token="1|abc")


async def test_authenticate_returns_token(client):
    with aioresponses() as m:
        m.post(f"{CLOUD_URL}/api/v1/edge/auth", payload={"token": "1|newtoken"})
        token = await client.authenticate("user@example.com", "secret", "Home Assistant")
    assert token == "1|newtoken"


async def test_authenticate_raises_auth_error_on_422(client):
    with aioresponses() as m:
        m.post(f"{CLOUD_URL}/api/v1/edge/auth", status=422)
        with pytest.raises(LazyVoltAuthError):
            await client.authenticate("bad@user.com", "wrong", "HA")


async def test_authenticate_raises_api_error_on_connection_failure(client):
    with aioresponses() as m:
        m.post(f"{CLOUD_URL}/api/v1/edge/auth", exception=aiohttp.ClientConnectionError())
        with pytest.raises(LazyVoltApiError):
            await client.authenticate("user@example.com", "secret", "HA")


async def test_get_decision_returns_mode(authed_client):
    with aioresponses() as m:
        m.get(
            f"{CLOUD_URL}/api/v1/edge/decision",
            payload={"mode": "SOLAR", "phases": 1, "amps": 6},
        )
        decision = await authed_client.get_decision()
    assert decision["mode"] == "SOLAR"


async def test_get_decision_raises_on_error(authed_client):
    with aioresponses() as m:
        m.get(f"{CLOUD_URL}/api/v1/edge/decision", status=500)
        with pytest.raises(LazyVoltApiError):
            await authed_client.get_decision()


async def test_post_telemetry_sends_payload(authed_client):
    with aioresponses() as m:
        m.post(f"{CLOUD_URL}/api/v1/edge/telemetry", status=204)
        await authed_client.post_telemetry({"mode": "SOLAR", "charger_status": "charging"})
    # No exception = success


async def test_post_progress_ignores_404_no_active_goal(authed_client):
    with aioresponses() as m:
        m.post(f"{CLOUD_URL}/api/v1/edge/progress", status=404)
        # Should not raise
        await authed_client.post_progress(1_000_000)


async def test_post_progress_sends_wh(authed_client):
    with aioresponses() as m:
        m.post(f"{CLOUD_URL}/api/v1/edge/progress", status=200, payload={"kwh_charged": 5.0})
        await authed_client.post_progress(5_000_000)
    # No exception = success
