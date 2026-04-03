"""
telegram_bot.py
───────────────
Uses Telethon StringSession — no session file needed on the server.
Session string is stored in environment variable TG_SESSION_STRING.

Driver name matching for groups like:
  "#001 / Salyh Orazlyyev / Express Route LLC"
  "Salyh Orazlyyev"
  "002 John Smith Transport"
"""

import re
import asyncio
import logging
from difflib import SequenceMatcher
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, UserDeactivatedBanError
from typing import Optional

logger = logging.getLogger(__name__)


def extract_name_from_group_title(title: str) -> str:
    """
    Extracts the driver name from a Telegram group title.

    Handles formats:
      "#001 / Salyh Orazlyyev / Express Route LLC"  → "Salyh Orazlyyev"
      "002 / John Smith / Smith LLC"                 → "John Smith"
      "John Smith"                                   → "John Smith"
      "#5 John Smith Transport Inc"                  → "John Smith"
    """
    # Format: "#001 / Name / Company" — split by slash
    if "/" in title:
        parts = [p.strip() for p in title.split("/")]
        for part in parts:
            # Skip truck number parts like "#001" or "001"
            if re.match(r"^#?\d+$", part):
                continue
            # Skip obvious company name parts
            if re.search(
                r"\b(LLC|INC|CORP|CO\b|COMPANY|TRANSPORT|TRUCKING|FREIGHT|"
                r"EXPRESS|LOGISTICS|CARRIERS|BROTHERS|SOLUTIONS|GROUP|SERVICES)\b",
                part, re.I
            ):
                continue
            # If it contains at least two words of letters, it's a name
            if len(re.findall(r"[A-Za-z]{2,}", part)) >= 1 and len(part) >= 3:
                return part.strip()

    # No slash format — strip leading truck number
    cleaned = re.sub(r"^#?\d+\s*", "", title).strip()
    # Strip trailing company keywords
    cleaned = re.sub(
        r"\s+(LLC|INC|CORP|CO\.|COMPANY|TRANSPORT|TRUCKING|FREIGHT|EXPRESS|"
        r"LOGISTICS|CARRIERS|GROUP|SERVICES)[\s.]*$",
        "", cleaned, flags=re.I
    ).strip()
    return cleaned


def name_similarity(name_a: str, name_b: str) -> float:
    """Returns 0.0–1.0 similarity between two names."""
    a = name_a.lower().strip()
    b = name_b.lower().strip()
    if a == b:
        return 1.0
    # Token-based: check if all tokens of the shorter name appear in longer
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if tokens_a <= tokens_b or tokens_b <= tokens_a:
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


class TelegramUserbot:
    """Telegram userbot using StringSession (no file storage required)."""

    MATCH_THRESHOLD = 0.70  # minimum similarity to consider a match

    def __init__(self, api_id: int, api_hash: str, session_string: str, name: str = "Account"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.name = name
        self.client: Optional[TelegramClient] = None
        # Cache: extracted_name → entity
        self._group_cache: dict[str, object] = {}
        # Cache: title (original) → extracted_name
        self._title_map: dict[str, str] = {}

    async def start(self):
        self.client = TelegramClient(
            StringSession(self.session_string),
            self.api_id,
            self.api_hash
        )
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise RuntimeError(
                f"Telegram session expired for {self.name}. "
                "Run generate_session.py again and update TG_SESSION_STRING."
            )
        me = await self.client.get_me()
        logger.info(f"[{self.name}] Logged in as {me.first_name} (@{me.username})")
        await self._refresh_cache()
        return self

    async def stop(self):
        if self.client:
            await self.client.disconnect()

    async def _refresh_cache(self):
        """Cache all groups with their extracted driver names."""
        self._group_cache.clear()
        self._title_map.clear()
        count = 0
        async for dialog in self.client.iter_dialogs():
            title = getattr(dialog.entity, "title", None)
            if title:
                extracted = extract_name_from_group_title(title)
                self._group_cache[extracted.lower()] = dialog.entity
                self._title_map[title] = extracted
                count += 1
        logger.info(f"[{self.name}] Cached {count} groups")

    def find_best_match(self, driver_name: str) -> tuple[Optional[object], str, float]:
        """
        Find the best matching Telegram group for a driver name.
        Returns (entity, matched_title, similarity_score).
        """
        best_entity = None
        best_score = 0.0
        best_title = ""

        for extracted_name, entity in self._group_cache.items():
            score = name_similarity(driver_name, extracted_name)
            if score > best_score:
                best_score = score
                best_entity = entity
                best_title = extracted_name

        if best_score >= self.MATCH_THRESHOLD:
            return best_entity, best_title, best_score
        return None, "", best_score

    async def send_to_driver(self, driver_name: str, message: str) -> tuple[bool, str]:
        """
        Send message to the group matching the driver name.
        Returns (success, group_title_used).
        """
        entity, matched_title, score = self.find_best_match(driver_name)

        if not entity:
            # Try refreshing cache first
            await self._refresh_cache()
            entity, matched_title, score = self.find_best_match(driver_name)

        if not entity:
            logger.warning(f"[{self.name}] No group found for driver: {driver_name}")
            return False, ""

        try:
            await self.client.send_message(entity, message)
            logger.info(
                f"[{self.name}] ✓ Sent to '{matched_title}' "
                f"(driver: {driver_name}, score: {score:.2f})"
            )
            return True, matched_title

        except FloodWaitError as e:
            logger.warning(f"[{self.name}] Flood wait {e.seconds}s")
            await asyncio.sleep(min(e.seconds, 60))
            return False, ""

        except Exception as e:
            logger.error(f"[{self.name}] Send failed for {driver_name}: {e}")
            return False, ""

    async def list_groups_with_drivers(self) -> list[dict]:
        """Returns all groups with their extracted driver names (for diagnostics)."""
        await self._refresh_cache()
        result = []
        for original_title, extracted in self._title_map.items():
            result.append({
                "group_title": original_title,
                "extracted_name": extracted,
            })
        return sorted(result, key=lambda x: x["extracted_name"])


class TelebotManager:
    """Manages multiple Telegram accounts with round-robin sending."""

    def __init__(self):
        self.accounts: list[TelegramUserbot] = []
        self._idx = 0

    def add(self, bot: TelegramUserbot):
        self.accounts.append(bot)

    async def send_alert(self, driver_name: str, message: str) -> tuple[bool, str]:
        """Send via next available account. Returns (success, group_name)."""
        if not self.accounts:
            logger.error("No Telegram accounts configured!")
            return False, ""

        for _ in range(len(self.accounts)):
            account = self.accounts[self._idx % len(self.accounts)]
            self._idx += 1
            success, group = await account.send_to_driver(driver_name, message)
            if success:
                return True, group

        return False, ""

    async def stop_all(self):
        for acc in self.accounts:
            await acc.stop()

    async def get_all_groups(self) -> list[dict]:
        """Get all groups from all accounts."""
        result = []
        for acc in self.accounts:
            groups = await acc.list_groups_with_drivers()
            for g in groups:
                g["account"] = acc.name
            result.extend(groups)
        return result
