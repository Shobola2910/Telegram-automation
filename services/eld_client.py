"""
ELD API Client — supports Factor ELD (drivehos.app) and future ELD providers.
Each ELD source can be configured independently via the database.
"""
import httpx
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HosData:
    """Normalized HOS data across all ELD providers"""
    driver_id: str
    driver_name: str
    driver_email: str
    company_id: str
    eld_source: str

    # Status
    status: str           # "D" Drive, "ON" On Duty, "OFF" Off Duty, "SB" Sleeper
    is_connected: bool    # ELD device online

    # Time remainders (hours)
    drive_remaining: float    # Remaining drive time
    shift_remaining: float    # Remaining on-duty (shift)
    break_remaining: float    # Remaining until break required
    cycle_remaining: float    # Remaining weekly cycle

    # Current activity duration (minutes)
    current_duration_min: int

    # Form/document status
    document_incomplete: bool
    profile_form_ok: bool
    profile_issues: str

    # Raw data for debugging
    raw: dict


class EldClientFactory:
    """Returns correct client based on ELD source name"""

    @staticmethod
    def get_client(source_name: str, base_url: str, bearer_token: str,
                   tenant_id: Optional[str] = None) -> "BaseEldClient":
        source_lower = source_name.lower()
        if source_lower in ("factor", "factoreld", "drivehos"):
            return FactorEldClient(base_url, bearer_token, tenant_id)
        elif source_lower in ("leader", "leadereld"):
            return LeaderEldClient(base_url, bearer_token, tenant_id)
        else:
            # Generic client — try Factor-compatible endpoints
            return FactorEldClient(base_url, bearer_token, tenant_id)


class BaseEldClient:
    def __init__(self, base_url: str, bearer_token: str, tenant_id: Optional[str]):
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.tenant_id = tenant_id
        self._client = httpx.AsyncClient(timeout=30)

    def _headers(self) -> dict:
        h = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.tenant_id:
            h["tenant_id"] = self.tenant_id
        return h

    async def get_companies(self) -> list[dict]:
        raise NotImplementedError

    async def get_drivers(self, company_id: str) -> list[dict]:
        raise NotImplementedError

    async def get_driver_hos(self, driver_id: str) -> Optional[HosData]:
        raise NotImplementedError

    async def get_all_drivers_hos(self) -> list[HosData]:
        raise NotImplementedError

    async def close(self):
        await self._client.aclose()


class FactorEldClient(BaseEldClient):
    """Client for Factor ELD (api.drivehos.app)"""

    async def get_companies(self) -> list[dict]:
        try:
            resp = await self._client.get(
                f"{self.base_url}/companies",
                headers=self._headers(),
                params={"status": "active", "limit": 100, "page": 1, "group": "all"}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", data) if isinstance(data, dict) else data
        except Exception as e:
            logger.error(f"[FactorELD] get_companies error: {e}")
            return []

    async def get_drivers(self, company_id: Optional[str] = None) -> list[dict]:
        try:
            params = {"limit": 200, "page": 1, "status": "active"}
            if company_id:
                params["company_id"] = company_id
            resp = await self._client.get(
                f"{self.base_url}/drivers",
                headers=self._headers(),
                params=params
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", data) if isinstance(data, dict) else data
        except Exception as e:
            logger.error(f"[FactorELD] get_drivers error: {e}")
            return []

    async def get_driver_hos(self, driver_id: str) -> Optional[HosData]:
        """Get HOS logs for a specific driver"""
        try:
            resp = await self._client.get(
                f"{self.base_url}/hos/drivers/{driver_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            raw = resp.json()
            return self._parse_hos(raw, driver_id)
        except Exception as e:
            logger.error(f"[FactorELD] get_driver_hos({driver_id}) error: {e}")
            return None

    async def get_all_drivers_hos(self) -> list[HosData]:
        """Fetch HOS summary for all active drivers"""
        try:
            resp = await self._client.get(
                f"{self.base_url}/hos/summary",
                headers=self._headers(),
                params={"limit": 500, "page": 1}
            )
            resp.raise_for_status()
            data = resp.json()
            records = data.get("data", data) if isinstance(data, dict) else data
            result = []
            for r in records:
                hos = self._parse_hos(r, r.get("driver_id", r.get("id", "")))
                if hos:
                    result.append(hos)
            return result
        except Exception as e:
            logger.error(f"[FactorELD] get_all_drivers_hos error: {e}")
            # Fallback: try per-driver
            return await self._fetch_all_per_driver()

    async def _fetch_all_per_driver(self) -> list[HosData]:
        drivers = await self.get_drivers()
        result = []
        for d in drivers:
            driver_id = d.get("id") or d.get("driver_id")
            if not driver_id:
                continue
            hos = await self.get_driver_hos(driver_id)
            if hos:
                result.append(hos)
        return result

    def _parse_hos(self, raw: dict, driver_id: str) -> Optional[HosData]:
        """Parse Factor ELD API response into normalized HosData"""
        try:
            # Driver info
            driver_info = raw.get("driver", raw)
            name = (
                driver_info.get("name") or
                f"{driver_info.get('first_name', '')} {driver_info.get('last_name', '')}".strip() or
                driver_info.get("full_name", "Unknown Driver")
            )
            email = driver_info.get("email", "")
            company_id = str(raw.get("company_id", raw.get("carrier_id", "")))

            # HOS clocks — Factor stores in seconds, convert to hours
            clocks = raw.get("clocks", raw.get("hos_clocks", {}))

            def to_hours(val) -> float:
                if val is None:
                    return 0.0
                # Could be seconds or already hours
                v = float(val)
                return v / 3600.0 if v > 100 else v

            drive_rem = to_hours(clocks.get("driving") or clocks.get("drive_remaining") or
                                  raw.get("drive_time_remaining") or raw.get("driving_remaining"))
            shift_rem = to_hours(clocks.get("on_duty") or clocks.get("shift_remaining") or
                                  raw.get("on_duty_remaining") or raw.get("shift_remaining"))
            break_rem = to_hours(clocks.get("break") or clocks.get("break_remaining") or
                                  raw.get("break_remaining"))
            cycle_rem = to_hours(clocks.get("cycle") or clocks.get("cycle_remaining") or
                                  raw.get("cycle_remaining"))

            # Status
            status_raw = (raw.get("current_status") or raw.get("status") or "OFF").upper()
            status_map = {"D": "D", "DRIVING": "D", "ON": "ON", "ON_DUTY": "ON",
                          "OFF": "OFF", "OFF_DUTY": "OFF", "SB": "SB", "SLEEPER": "SB"}
            status = status_map.get(status_raw, status_raw[:2])

            # Connection
            device = raw.get("device", raw.get("eld_device", {}))
            is_connected = (
                device.get("connected", device.get("is_connected", True))
                if isinstance(device, dict) else True
            )

            # Duration of current activity (minutes)
            dur_min = int(raw.get("current_duration", raw.get("duration_minutes", 0)) or 0)

            # Document / form check
            doc = raw.get("document", raw.get("logbook", {}))
            doc_incomplete = not doc.get("complete", True) if isinstance(doc, dict) else False

            profile = raw.get("profile", {})
            profile_issues = ""
            profile_ok = True
            if isinstance(profile, dict):
                missing = [k for k in ("license_number", "license_state", "license_expiry")
                           if not profile.get(k)]
                if missing:
                    profile_ok = False
                    profile_issues = f"Yetishmaydi: {', '.join(missing)}"

            return HosData(
                driver_id=str(driver_id),
                driver_name=name,
                driver_email=email,
                company_id=company_id,
                eld_source="factor",
                status=status,
                is_connected=bool(is_connected),
                drive_remaining=round(drive_rem, 2),
                shift_remaining=round(shift_rem, 2),
                break_remaining=round(break_rem, 2),
                cycle_remaining=round(cycle_rem, 2),
                current_duration_min=dur_min,
                document_incomplete=doc_incomplete,
                profile_form_ok=profile_ok,
                profile_issues=profile_issues,
                raw=raw,
            )
        except Exception as e:
            logger.error(f"[FactorELD] _parse_hos error for {driver_id}: {e}")
            return None


class LeaderEldClient(BaseEldClient):
    """Client for Leader ELD — implement when API docs available"""

    async def get_companies(self) -> list[dict]:
        logger.info("[LeaderELD] get_companies — implement with Leader ELD API docs")
        return []

    async def get_drivers(self, company_id: Optional[str] = None) -> list[dict]:
        logger.info("[LeaderELD] get_drivers — implement with Leader ELD API docs")
        return []

    async def get_driver_hos(self, driver_id: str) -> Optional[HosData]:
        logger.info("[LeaderELD] get_driver_hos — implement with Leader ELD API docs")
        return None

    async def get_all_drivers_hos(self) -> list[HosData]:
        logger.info("[LeaderELD] get_all_drivers_hos — implement with Leader ELD API docs")
        return []
