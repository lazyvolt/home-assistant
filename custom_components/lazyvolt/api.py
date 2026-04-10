"""LazyVolt Cloud API client."""
from __future__ import annotations

import aiohttp


class LazyVoltApiError(Exception):
    """Raised when an API call fails."""


class LazyVoltAuthError(LazyVoltApiError):
    """Raised on 401/422 authentication failures."""


class LazyVoltApiClient:
    """Async HTTP client for the LazyVolt Cloud edge API."""

    def __init__(
        self,
        cloud_url: str,
        session: aiohttp.ClientSession,
        token: str | None = None,
    ) -> None:
        self._cloud_url = cloud_url.rstrip("/")
        self._session = session
        self._token = token

    @property
    def token(self) -> str | None:
        return self._token

    @token.setter
    def token(self, value: str) -> None:
        self._token = value

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def authenticate(self, email: str, password: str, edge_name: str) -> str:
        """POST /api/v1/edge/auth — returns permanent Sanctum token."""
        url = f"{self._cloud_url}/api/v1/edge/auth"
        try:
            async with self._session.post(
                url,
                json={"email": email, "password": password, "edge_name": edge_name},
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (401, 422):
                    raise LazyVoltAuthError("Invalid credentials")
                resp.raise_for_status()
                data = await resp.json()
                return data["token"]
        except LazyVoltAuthError:
            raise
        except aiohttp.ClientError as err:
            raise LazyVoltApiError(f"Cannot connect to LazyVolt Cloud: {err}") from err

    async def get_decision(self) -> dict:
        """GET /api/v1/edge/decision — returns {mode, phases, amps}."""
        url = f"{self._cloud_url}/api/v1/edge/decision"
        try:
            async with self._session.get(
                url,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise LazyVoltApiError(f"Error fetching decision: {err}") from err

    async def post_telemetry(self, data: dict) -> None:
        """POST /api/v1/edge/telemetry — fire-and-forget, best effort."""
        url = f"{self._cloud_url}/api/v1/edge/telemetry"
        try:
            async with self._session.post(
                url,
                json=data,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
        except aiohttp.ClientError as err:
            raise LazyVoltApiError(f"Error posting telemetry: {err}") from err

    async def post_progress(self, meter_energy_total_wh: int) -> None:
        """POST /api/v1/edge/progress — 404 (no active goal) is silently ignored."""
        url = f"{self._cloud_url}/api/v1/edge/progress"
        try:
            async with self._session.post(
                url,
                json={"meter_energy_total_wh": meter_energy_total_wh},
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 404:
                    return  # no active goal — normal
                resp.raise_for_status()
        except aiohttp.ClientError as err:
            raise LazyVoltApiError(f"Error posting progress: {err}") from err
