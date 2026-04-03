"""
eld_client.py — Factor ELD and Leader ELD API clients
"""

import aiohttp
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ELDDriver:
    def __init__(self, data: dict, account_name: str):
        self.id          = str(data.get("id") or data.get("driver_id", ""))
        self.full_name   = self._name(data)
        self.status      = (data.get("current_duty_status")
                            or data.get("duty_status", "unknown"))
        self.status_since = (data.get("current_status_since")
                             or data.get("duty_status_start_time"))
        self.connected   = data.get("eld_connection_status", "connected") != "disconnected"
        self.account_name = account_name

        hos = data.get("hos_clocks") or data.get("hos") or {}
        clocks = {
            "drive": hos.get("drive", {}),
            "shift": hos.get("shift", {}),
            "break": hos.get("break", {}),
            "cycle": hos.get("cycle", {}),
        }
        self.drive_remaining_sec  = (clocks["drive"].get("time_remaining")
                                     or data.get("drive_remaining_seconds", 0))
        self.shift_remaining_sec  = (clocks["shift"].get("time_remaining")
                                     or data.get("shift_remaining_seconds", 0))
        self.break_remaining_sec  = (clocks["break"].get("time_remaining")
                                     or data.get("break_remaining_seconds", 0))
        self.cycle_remaining_sec  = (clocks["cycle"].get("time_remaining")
                                     or data.get("cycle_remaining_seconds", 0))

        self.drive_violation = data.get("drive_violation", False)
        self.has_pti         = data.get("has_pti", True)
        self.last_profile_update = (data.get("last_profile_updated_at")
                                    or data.get("form_updated_at"))
        self.logs_certified  = data.get("logs_certified", True)
        self.uncertified_days = data.get("uncertified_log_days", 0)

    def _name(self, d: dict) -> str:
        if d.get("full_name"):
            return d["full_name"]
        first = d.get("first_name", "")
        last  = d.get("last_name", "")
        if first or last:
            return f"{first} {last}".strip()
        return d.get("name", d.get("username", "Unknown"))

    @property
    def drive_remaining_hours(self): return self.drive_remaining_sec / 3600
    @property
    def shift_remaining_hours(self): return self.shift_remaining_sec / 3600
    @property
    def break_remaining_hours(self): return self.break_remaining_sec / 3600
    @property
    def cycle_remaining_hours(self): return self.cycle_remaining_sec / 3600

    def status_duration_minutes(self) -> Optional[float]:
        if not self.status_since:
            return None
        try:
            if isinstance(self.status_since, str):
                since = datetime.fromisoformat(self.status_since.replace("Z", "+00:00"))
            else:
                since = datetime.fromtimestamp(self.status_since, tz=timezone.utc)
            return (datetime.now(timezone.utc) - since).total_seconds() / 60
        except Exception:
            return None


class BaseELDClient:
    def __init__(self, token: str, base_url: str, account_name: str):
        self.token        = token
        self.base_url     = base_url.rstrip("/")
        self.account_name = account_name
        self._session: Optional[aiohttp.ClientSession] = None

    def _session_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ELDMonitor/2.0",
        }

    def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._session_headers())
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, path: str) -> Optional[dict]:
        session = self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 401:
                    logger.error(f"[{self.account_name}] 401 Unauthorized — token expired")
                    return None
                if resp.status == 404:
                    logger.debug(f"[{self.account_name}] 404 {url}")
                    return None
                if resp.status >= 400:
                    logger.warning(f"[{self.account_name}] HTTP {resp.status} for {url}")
                    return None
                return await resp.json()
        except aiohttp.ClientError as e:
            logger.error(f"[{self.account_name}] Request failed: {url} — {e}")
            return None

    async def _try_endpoints(self, endpoints: list[str]) -> Optional[dict]:
        for ep in endpoints:
            data = await self._get(ep)
            if data is not None:
                return data
        return None

    def _extract_list(self, data: dict | list | None) -> list:
        if data is None:
            return []
        if isinstance(data, list):
            return data
        # common wrappers: {"data": [...]} or {"drivers": [...]} or {"results": [...]}
        for key in ("data", "drivers", "results", "items", "records"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return []


class FactorELDClient(BaseELDClient):
    """
    Factor ELD — factorhq.com
    Tries multiple endpoint patterns since API versions vary.
    """
    DRIVER_ENDPOINTS = [
        "/v1/company/drivers",
        "/v2/company/drivers",
        "/v1/drivers",
        "/api/v1/drivers",
    ]
    HOS_ENDPOINTS_TPL = [
        "/v1/drivers/{id}/hos_clocks",
        "/v2/drivers/{id}/hos",
        "/v1/hos_logs?driver_id={id}&latest=true",
    ]

    def __init__(self, token: str, base_url: str = "", account_name: str = "Factor ELD"):
        super().__init__(token, base_url or os.getenv("FACTOR_ELD_URL", "https://api.factorhq.com"), account_name)

    async def get_all_driver_data(self) -> list[ELDDriver]:
        raw = await self._try_endpoints(self.DRIVER_ENDPOINTS)
        rows = self._extract_list(raw)
        if not rows:
            logger.warning(f"[{self.account_name}] No drivers returned — check token/endpoints")
            return []

        drivers = [ELDDriver(r, self.account_name) for r in rows]

        # Enrich with HOS if missing
        for driver in drivers:
            if driver.drive_remaining_sec == 0 and driver.shift_remaining_sec == 0:
                endpoints = [ep.format(id=driver.id) for ep in self.HOS_ENDPOINTS_TPL]
                hos_raw = await self._try_endpoints(endpoints)
                if hos_raw:
                    hos = self._extract_list(hos_raw)
                    if hos and isinstance(hos[0], dict):
                        hos_data = hos[0]
                    else:
                        hos_data = hos_raw if isinstance(hos_raw, dict) else {}
                    driver.drive_remaining_sec = hos_data.get("drive_remaining_seconds", 0)
                    driver.shift_remaining_sec = hos_data.get("shift_remaining_seconds", 0)
                    driver.cycle_remaining_sec = hos_data.get("cycle_remaining_seconds", 0)
                    driver.break_remaining_sec = hos_data.get("break_remaining_seconds", 0)

        logger.info(f"[{self.account_name}] Fetched {len(drivers)} drivers")
        return drivers


class LeaderELDClient(BaseELDClient):
    """
    Leader ELD
    Endpoint patterns — adjust if needed based on their API docs.
    """
    DRIVER_ENDPOINTS = [
        "/v1/drivers",
        "/api/v1/drivers",
        "/api/drivers",
        "/v2/drivers",
    ]

    def __init__(self, token: str, base_url: str = "", account_name: str = "Leader ELD"):
        super().__init__(token, base_url or os.getenv("LEADER_ELD_URL", "https://api.leadereld.com"), account_name)

    async def get_all_driver_data(self) -> list[ELDDriver]:
        raw = await self._try_endpoints(self.DRIVER_ENDPOINTS)
        rows = self._extract_list(raw)
        if not rows:
            logger.warning(f"[{self.account_name}] No drivers returned")
            return []
        drivers = [ELDDriver(r, self.account_name) for r in rows]
        logger.info(f"[{self.account_name}] Fetched {len(drivers)} drivers")
        return drivers


def create_eld_client(cfg: dict) -> BaseELDClient:
    eld_type = cfg.get("type", "factor").lower()
    token    = cfg["token"]
    base_url = cfg.get("base_url", "")
    name     = cfg.get("name", "ELD")
    if eld_type == "factor":
        return FactorELDClient(token, base_url, name)
    if eld_type == "leader":
        return LeaderELDClient(token, base_url, name)
    raise ValueError(f"Unknown ELD type: {eld_type}")
