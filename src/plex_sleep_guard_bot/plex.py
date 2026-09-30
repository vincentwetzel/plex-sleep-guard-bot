"""Plex sessions polling and XML parsing."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from xml.etree import ElementTree

import aiohttp

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PlexSession:
    title: str
    media_type: str
    state: str
    session_key: str


@dataclass(frozen=True, slots=True)
class PlexPollResult:
    succeeded: bool
    sessions: tuple[PlexSession, ...] = ()
    error: str | None = None

    @property
    def has_active_sessions(self) -> bool:
        return bool(self.sessions)


def parse_sessions(xml: bytes | str) -> tuple[PlexSession, ...]:
    """Return active media sessions; any non-stopped state counts as active."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        raise

    sessions: list[PlexSession] = []
    for element in root:
        media_type = element.attrib.get("type", "").strip()
        state = element.attrib.get("state", "unknown").strip()
        if not media_type or state.casefold() == "stopped":
            continue
        title = (
            element.attrib.get("grandparentTitle")
            or element.attrib.get("parentTitle")
            or element.attrib.get("title")
            or "(untitled)"
        )
        sessions.append(PlexSession(title, media_type, state, element.attrib.get("sessionKey", "")))
    return tuple(sessions)


class PlexMonitor:
    def __init__(self, server_url: str, token: str, timeout_seconds: int = 15) -> None:
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def poll(self) -> PlexPollResult:
        if self._session is None:
            await self.start()
        assert self._session is not None
        headers = {"Accept": "application/xml"}
        if self.token:
            headers["X-Plex-Token"] = self.token
        url = f"{self.server_url}/status/sessions"
        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status < 200 or response.status >= 300:
                    reason = f"Plex returned HTTP {response.status} ({response.reason})."
                    logger.error("%s", reason)
                    return PlexPollResult(False, error=reason)
                body = await response.read()
            try:
                sessions = parse_sessions(body)
            except ElementTree.ParseError as exc:
                reason = f"Plex returned invalid XML: {exc}"
                logger.error("%s", reason)
                return PlexPollResult(False, error=reason)
            return PlexPollResult(True, sessions)
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
            reason = f"Plex request failed: {exc}"
            logger.error("%s", reason)
            return PlexPollResult(False, error=reason)

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
