"""
fmcsa.py — FMCSA Carrier lookup by USDOT number
Uses FMCSA public API (free key required) or SAFER web fallback.

Get free API key: https://ask.fmcsa.dot.gov/app/answers/detail/a_id/27
"""

import aiohttp
import os
import logging
import re

logger = logging.getLogger(__name__)

FMCSA_WEB_KEY = os.getenv("FMCSA_WEB_KEY", "")
FMCSA_API_URL = "https://mobile.fmcsa.dot.gov/qc/services/carriers"


async def lookup_by_usdot(usdot: str) -> dict:
    """
    Look up a carrier by USDOT number.
    Returns dict with keys: usdot, name, mc_number, address, state, status
    Returns empty dict if not found.
    """
    usdot = usdot.strip().lstrip("0")

    # Try FMCSA official API first (requires webKey)
    if FMCSA_WEB_KEY:
        result = await _fmcsa_api_lookup(usdot)
        if result:
            return result

    # Fallback: SAFER web scrape
    return await _safer_web_lookup(usdot)


async def _fmcsa_api_lookup(usdot: str) -> dict:
    url = f"{FMCSA_API_URL}/{usdot}?webKey={FMCSA_WEB_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()
                carrier = data.get("content", {}).get("carrier", {})
                if not carrier:
                    return {}
                return {
                    "usdot": usdot,
                    "name": carrier.get("legalName") or carrier.get("dbaName", ""),
                    "mc_number": str(carrier.get("mcNumber", "")),
                    "address": _format_address(carrier),
                    "status": carrier.get("dotOperatingStatus", ""),
                }
    except Exception as e:
        logger.warning(f"FMCSA API error for USDOT {usdot}: {e}")
        return {}


async def _safer_web_lookup(usdot: str) -> dict:
    """Fallback: scrape SAFER web for basic company info."""
    url = f"https://safer.fmcsa.dot.gov/query.asp?searchtype=ANY&query_type=queryCarrierSnapshot&query_param=USDOT&query_string={usdot}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "Mozilla/5.0"}
            ) as resp:
                if resp.status != 200:
                    return {}
                html = await resp.text()
                return _parse_safer_html(usdot, html)
    except Exception as e:
        logger.warning(f"SAFER scrape error for USDOT {usdot}: {e}")
        return {}


def _parse_safer_html(usdot: str, html: str) -> dict:
    """Extract company name from SAFER HTML response."""
    # Legal name
    name_match = re.search(
        r"Legal Name[:\s]*</th>\s*<td[^>]*>(.*?)</td>", html, re.I | re.S
    )
    name = ""
    if name_match:
        name = re.sub(r"<[^>]+>", "", name_match.group(1)).strip()

    if not name:
        return {}

    # MC number
    mc_match = re.search(r"MC/MX/FF Number[^:]*:\s*(\d+)", html, re.I)
    mc = mc_match.group(1) if mc_match else ""

    # State
    state_match = re.search(r"State:\s*</td>\s*<td[^>]*>([A-Z]{2})</td>", html)
    state = state_match.group(1) if state_match else ""

    return {
        "usdot": usdot,
        "name": name,
        "mc_number": mc,
        "address": state,
        "status": "Active",
    }


def _format_address(carrier: dict) -> str:
    parts = [
        carrier.get("phyStreet", ""),
        carrier.get("phyCity", ""),
        carrier.get("phyState", ""),
        carrier.get("phyZipcode", ""),
    ]
    return ", ".join(p for p in parts if p)
