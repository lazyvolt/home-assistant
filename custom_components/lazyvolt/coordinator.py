"""LazyVolt DataUpdateCoordinator."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LazyVoltApiClient, LazyVoltApiError
from .const import (
    CLOUD_MODE_TO_PEBLAR,
    DOMAIN,
    PEBLAR_CP_STATE_TO_CLOUD_STATUS,
    PEBLAR_DOMAIN,
    PEBLAR_SELECT_SMART_CHARGING,
    PEBLAR_SENSOR_CP_STATE,
    PEBLAR_SENSOR_CURRENT_PHASE1,
    PEBLAR_SENSOR_CURRENT_PHASE2,
    PEBLAR_SENSOR_CURRENT_PHASE3,
    PEBLAR_SENSOR_ENERGY_TOTAL,
    PEBLAR_SENSOR_ENERGY_SESSION,
    PEBLAR_SENSOR_POWER_PHASE1,
    PEBLAR_SENSOR_POWER_PHASE2,
    PEBLAR_SENSOR_POWER_PHASE3,
    PEBLAR_SWITCH_CHARGE,
    PEBLAR_SWITCH_FORCE_SINGLE_PHASE,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _find_entity_id(
    registry: er.EntityRegistry, peblar_entry_id: str, domain: str, translation_key: str
) -> str | None:
    """Return entity_id for a Peblar entity by platform domain and translation_key."""
    for entry in registry.entities.values():
        if (
            entry.config_entry_id == peblar_entry_id
            and entry.platform == PEBLAR_DOMAIN
            and entry.domain == domain
            and entry.translation_key == translation_key
        ):
            return entry.entity_id
    return None


def _float_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Return float state of an entity, or None if unavailable/missing."""
    if entity_id is None:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unavailable", "unknown", ""):
        return None
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return None


def _str_state(hass: HomeAssistant, entity_id: str | None) -> str | None:
    """Return string state of an entity, or None if unavailable/missing."""
    if entity_id is None:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unavailable", "unknown", ""):
        return None
    return state.state


class LazyVoltCoordinator(DataUpdateCoordinator):
    """Polls Cloud for charge decisions, applies them to Peblar, posts telemetry."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: LazyVoltApiClient,
        peblar_entry_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self._api = api
        self._peblar_entry_id = peblar_entry_id
        self._entity_ids: dict[str, str | None] = {}

    def setup_entity_ids(self) -> None:
        """Resolve Peblar entity IDs from the entity registry. Call after HA is ready."""
        registry = er.async_get(self.hass)
        self._entity_ids = {
            "smart_charging": _find_entity_id(registry, self._peblar_entry_id, "select", PEBLAR_SELECT_SMART_CHARGING),
            "cp_state": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_CP_STATE),
            "energy_total": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_ENERGY_TOTAL),
            "energy_session": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_ENERGY_SESSION),
            "power_phase_1": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_POWER_PHASE1),
            "power_phase_2": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_POWER_PHASE2),
            "power_phase_3": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_POWER_PHASE3),
            "current_phase_1": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_CURRENT_PHASE1),
            "current_phase_2": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_CURRENT_PHASE2),
            "current_phase_3": _find_entity_id(registry, self._peblar_entry_id, "sensor", PEBLAR_SENSOR_CURRENT_PHASE3),
            "charge": _find_entity_id(registry, self._peblar_entry_id, "switch", PEBLAR_SWITCH_CHARGE),
            "force_single_phase": _find_entity_id(registry, self._peblar_entry_id, "switch", PEBLAR_SWITCH_FORCE_SINGLE_PHASE),
        }
        _LOGGER.debug("Resolved Peblar entity IDs: %s", self._entity_ids)

    async def _async_update_data(self) -> dict:
        try:
            decision = await self._api.get_decision()
        except LazyVoltApiError as err:
            raise UpdateFailed(str(err)) from err

        mode = decision.get("mode", "SOLAR")

        await self._apply_mode(mode)

        peblar = self._read_peblar_state()

        try:
            await self._api.post_telemetry({
                "charger_watts": peblar.get("power_total"),
                "charger_amps": peblar.get("current_phase_1"),
                "charger_phases": peblar.get("phases"),
                "charger_on": peblar.get("charge_on"),
                "kwh_session": peblar.get("energy_session"),
                "charger_status": peblar.get("cloud_status"),
                "mode": mode,
            })
        except LazyVoltApiError:
            _LOGGER.warning("Failed to post telemetry", exc_info=True)

        if (energy_total := peblar.get("energy_total")) is not None:
            try:
                await self._api.post_progress(int(energy_total * 1000))
            except LazyVoltApiError:
                _LOGGER.warning("Failed to post progress", exc_info=True)

        return {"mode": mode, "decision": decision, **peblar}

    async def _apply_mode(self, mode: str) -> None:
        """Set the Peblar charger to the mode dictated by Cloud."""
        charge_entity = self._entity_ids.get("charge")
        smart_charging_entity = self._entity_ids.get("smart_charging")

        if mode == "STANDBY":
            if charge_entity:
                await self.hass.services.async_call(
                    "switch", "turn_off",
                    {"entity_id": charge_entity},
                    blocking=True,
                )
            return

        # SOLAR or MAX: ensure charger is on
        if charge_entity:
            current = _str_state(self.hass, charge_entity)
            if current != "on":
                await self.hass.services.async_call(
                    "switch", "turn_on",
                    {"entity_id": charge_entity},
                    blocking=True,
                )

        peblar_option = CLOUD_MODE_TO_PEBLAR.get(mode)
        if peblar_option and smart_charging_entity:
            current_option = _str_state(self.hass, smart_charging_entity)
            if current_option != peblar_option:
                await self.hass.services.async_call(
                    "select", "select_option",
                    {"entity_id": smart_charging_entity, "option": peblar_option},
                    blocking=True,
                )

    def _read_peblar_state(self) -> dict:
        """Read current Peblar entity states and return normalised telemetry fields."""
        hass = self.hass

        cp_state_raw = _str_state(hass, self._entity_ids.get("cp_state"))
        cloud_status = PEBLAR_CP_STATE_TO_CLOUD_STATUS.get(cp_state_raw or "", "unreachable")

        # Power: sum available phase sensors (disabled by default in Peblar, may be None)
        p1 = _float_state(hass, self._entity_ids.get("power_phase_1"))
        p2 = _float_state(hass, self._entity_ids.get("power_phase_2"))
        p3 = _float_state(hass, self._entity_ids.get("power_phase_3"))
        power_total = int(sum(v for v in (p1, p2, p3) if v is not None)) if any(v is not None for v in (p1, p2, p3)) else None

        # Phases: force_single_phase on → 1, off → 3
        force_single = _str_state(hass, self._entity_ids.get("force_single_phase"))
        phases = 1 if force_single == "on" else 3

        # charger_on: True when cp_state is "charging"
        charge_on = cp_state_raw == "charging"

        return {
            "cp_state": cp_state_raw,
            "cloud_status": cloud_status,
            "power_total": power_total,
            "current_phase_1": _float_state(hass, self._entity_ids.get("current_phase_1")),
            "current_phase_2": _float_state(hass, self._entity_ids.get("current_phase_2")),
            "current_phase_3": _float_state(hass, self._entity_ids.get("current_phase_3")),
            "phases": phases,
            "charge_on": charge_on,
            "energy_total": _float_state(hass, self._entity_ids.get("energy_total")),
            "energy_session": _float_state(hass, self._entity_ids.get("energy_session")),
        }
