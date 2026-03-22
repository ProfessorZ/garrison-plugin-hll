"""Garrison plugin for Hell Let Loose dedicated servers."""

import json
import logging
import re
from datetime import datetime, timezone

try:
    from app.plugins.base import GamePlugin, PlayerInfo, ServerStatus, CommandDef, ServerOption
except ImportError:
    from dataclasses import dataclass, field
    from abc import ABC, abstractmethod
    from typing import Optional

    @dataclass
    class PlayerInfo:
        name: str
        steam_id: Optional[str] = None

    @dataclass
    class ServerStatus:
        online: bool
        player_count: int = 0
        version: Optional[str] = None
        extra: dict = field(default_factory=dict)

    @dataclass
    class CommandParam:
        name: str
        type: str
        required: bool = True
        description: str = ""
        choices: list[str] = field(default_factory=list)
        default: Optional[str] = None

    @dataclass
    class CommandDef:
        name: str
        description: str
        category: str
        params: list[CommandParam] = field(default_factory=list)
        admin_only: bool = False
        example: str = ""

    @dataclass
    class ServerOption:
        name: str
        value: str
        option_type: str
        category: str = "General"
        description: str = ""
        min_val: Optional[float] = None
        max_val: Optional[float] = None
        choices: list[str] = field(default_factory=list)

    class GamePlugin(ABC):
        PLUGIN_API_VERSION = 1
        custom_connection: bool = False

        @property
        @abstractmethod
        def game_type(self) -> str: ...

        @property
        @abstractmethod
        def display_name(self) -> str: ...

        @abstractmethod
        async def parse_players(self, raw_response: str) -> list: ...

        @abstractmethod
        async def get_status(self, send_command) -> ServerStatus: ...

        @abstractmethod
        def get_commands(self) -> list: ...

        def format_command(self, command: str) -> str:
            return command

        async def get_options(self, send_command) -> list:
            return []

        async def set_option(self, send_command, name: str, value: str) -> str:
            raise NotImplementedError

        async def kick_player(self, send_command, name: str, reason: str = "") -> str:
            raise NotImplementedError

        async def ban_player(self, send_command, name: str, reason: str = "") -> str:
            raise NotImplementedError

        async def unban_player(self, send_command, name: str) -> str:
            raise NotImplementedError

        async def connect_custom(self, host: str, port: int, password: str) -> None:
            raise NotImplementedError

        async def disconnect_custom(self) -> None:
            raise NotImplementedError

        async def send_command_custom(self, command: str, content: str = "") -> str:
            raise NotImplementedError
from hll_connection import HLLConnection

logger = logging.getLogger(__name__)


class HLLPlugin(GamePlugin):
    """Hell Let Loose RCON plugin using the XOR plaintext protocol."""

    custom_connection = True

    def __init__(self):
        self._connection: HLLConnection | None = None

    @property
    def game_type(self) -> str:
        return "hll"

    @property
    def display_name(self) -> str:
        return "Hell Let Loose"

    # ── Custom connection lifecycle ────────────────────────────────

    async def connect_custom(self, host: str, port: int, password: str) -> None:
        if self._connection and self._connection.connected:
            await self._connection.close()
        self._connection = HLLConnection(host, port, password)
        await self._connection.connect()

    async def disconnect_custom(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def send_command_custom(self, command: str, content: str | dict = "") -> str:
        """Send an HLL RCON command and return the response contentBody."""
        if not self._connection or not self._connection.connected:
            return "ERROR: Not connected"
        # When called from the console with a single string like "Kick name reason",
        # split the first word as the command name.
        if isinstance(content, str) and not content and " " in command:
            command, content = command.split(" ", 1)
        return await self._connection.send(command, content)

    # ── GamePlugin interface ───────────────────────────────────────

    async def parse_players(self, raw_response: str) -> list[PlayerInfo]:
        """Parse the GetServerInformation players response.

        The API returns JSON like: {"players": [{"name": "...", "steamId": "..."}, ...]}
        Falls back to the old line-based format if JSON parsing fails.
        """
        try:
            data = json.loads(raw_response) if isinstance(raw_response, str) else raw_response
            if isinstance(data, dict) and "players" in data:
                return [
                    PlayerInfo(
                        name=p.get("name", "Unknown"),
                        steam_id=p.get("steamId"),
                    )
                    for p in data["players"]
                ]
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: line-based "Name : SteamID" format
        players = []
        for line in raw_response.splitlines():
            line = line.strip()
            if not line:
                continue
            if " : " in line:
                name, steam_id = line.rsplit(" : ", 1)
                players.append(PlayerInfo(name=name.strip(), steam_id=steam_id.strip()))
            else:
                players.append(PlayerInfo(name=line))
        return players

    async def get_status(self, send_command) -> ServerStatus:
        try:
            session_raw = await send_command(
                "GetServerInformation", {"Name": "session", "Value": ""}
            )
            try:
                session = json.loads(session_raw) if isinstance(session_raw, str) else session_raw
            except (json.JSONDecodeError, TypeError):
                session = {}

            extra: dict = {}
            if session.get("serverName"):
                extra["server_name"] = session["serverName"]
            if session.get("mapId"):
                extra["map"] = session["mapId"]  # use mapId (e.g. "carentan_warfare") not mapName
            elif session.get("mapName"):
                extra["map"] = session["mapName"]
            if session.get("gameMode"):
                extra["game_mode"] = session["gameMode"]
            if "remainingMatchTime" in session:
                extra["remaining_time"] = session["remainingMatchTime"]
            if "matchTime" in session:
                extra["match_time"] = session["matchTime"]

            # Use playerCount from session data (slots endpoint returns empty)
            current = int(session.get("playerCount", 0))
            maximum = int(session.get("maxPlayers", 0))

            extra["max_players"] = maximum

            return ServerStatus(
                online=True,
                player_count=current,
                extra=extra,
            )
        except Exception:
            return ServerStatus(online=False, player_count=0)

    def get_commands(self) -> list[CommandDef]:
        from schema import get_commands
        return get_commands()

    async def get_options(self, send_command) -> list[ServerOption]:
        from options import fetch_options
        return await fetch_options(send_command)

    async def set_option(self, send_command, name: str, value: str) -> str:
        from options import set_option
        return await set_option(send_command, name, value)

    async def kick_player(self, send_command, name: str, reason: str = "") -> str:
        reason = reason or "Kicked by admin"
        result = await send_command("Kick", f"{name} {reason}")
        if result.upper().startswith("SUCCESS"):
            return f"Kicked {name}"
        return f"Kick failed: {result}"

    async def ban_player(self, send_command, name: str, reason: str = "") -> str:
        # Look up steam ID first
        raw = await send_command(
            "GetServerInformation", {"Name": "players", "Value": ""}
        )
        players = await self.parse_players(raw)
        player = next((p for p in players if p.name == name), None)
        if not player or not player.steam_id:
            return f"Error: player '{name}' not found or has no Steam ID"
        reason = reason or "Banned by admin"
        result = await send_command("BanById", f"{player.steam_id} {reason}")
        if result.upper().startswith("SUCCESS"):
            return f"Permanently banned {name} ({player.steam_id})"
        return f"Ban failed: {result}"

    async def unban_player(self, send_command, name: str) -> str:
        # name is treated as a Steam ID for unbans
        result = await send_command("PardonById", name)
        if result.upper().startswith("SUCCESS"):
            return f"Unbanned {name}"
        return f"Unban failed: {result}"

    # ── Event polling ──────────────────────────────────────────────

    # Regex patterns for HLL structured log lines
    _RE_KILL = re.compile(
        r"^(?:TEAM )?KILL: (.+?)\((.+?)/(\d+)\) -> (.+?)\((.+?)/(\d+)\) with (.+)$"
    )
    _RE_CHAT = re.compile(
        r"^CHAT\[(\w+)\]\[(.+?)\((.+?)/(\d+)\)\]: (.+)$"
    )
    _RE_CONNECT = re.compile(r"^CONNECTED (.+?) \((\d+)\)$")
    _RE_DISCONNECT = re.compile(r"^DISCONNECTED (.+?) \((\d+)\)$")
    _RE_KICK = re.compile(r"^KICK: \[(.+?)\] (?:has been kicked\.?\s*)?(?:\[(.+)\])?$")
    _RE_BAN = re.compile(r"^BAN: \[(.+?)\].*$")

    # Regex to strip the time prefix from GetAdminLog messages:
    # "[3:01 min (1774199517)] CHAT[Team]..." -> "CHAT[Team]..."
    _RE_LOG_PREFIX = re.compile(r"^\[\d+:\d{2} min \(\d+\)\] ")

    def _parse_log_line(self, line: str, now: datetime) -> dict | None:
        # Strip the time prefix added by GetAdminLog
        line = self._RE_LOG_PREFIX.sub("", line).strip()
        if not line:
            return None
        """Parse a single HLL log line into an event dict."""
        line = line.strip()
        if not line:
            return None

        # Kill / Team Kill
        m = self._RE_KILL.match(line)
        if m:
            is_tk = line.startswith("TEAM KILL")
            return {
                "event_type": "teamkill" if is_tk else "kill",
                "timestamp": now.isoformat(),
                "player_name": m.group(1).strip(),
                "player_id": m.group(3),
                "target_name": m.group(4).strip(),
                "target_id": m.group(6),
                "weapon": m.group(7).strip(),
                "raw": line,
            }

        # Chat
        m = self._RE_CHAT.match(line)
        if m:
            return {
                "event_type": "chat",
                "timestamp": now.isoformat(),
                "player_name": m.group(2).strip(),
                "player_id": m.group(4),
                "message": m.group(5).strip(),
                "raw": line,
            }

        # Connect
        m = self._RE_CONNECT.match(line)
        if m:
            return {
                "event_type": "connect",
                "timestamp": now.isoformat(),
                "player_name": m.group(1).strip(),
                "player_id": m.group(2),
                "raw": line,
            }

        # Disconnect
        m = self._RE_DISCONNECT.match(line)
        if m:
            return {
                "event_type": "disconnect",
                "timestamp": now.isoformat(),
                "player_name": m.group(1).strip(),
                "player_id": m.group(2),
                "raw": line,
            }

        # Kick
        m = self._RE_KICK.match(line)
        if m:
            return {
                "event_type": "kick",
                "timestamp": now.isoformat(),
                "player_name": m.group(1).strip(),
                "message": m.group(2).strip() if m.group(2) else None,
                "raw": line,
            }

        # Ban
        m = self._RE_BAN.match(line)
        if m:
            return {
                "event_type": "ban",
                "timestamp": now.isoformat(),
                "player_name": m.group(1).strip(),
                "raw": line,
            }

        return None

    async def poll_events(self, send_command, since: str | None = None) -> list[dict]:
        """Poll HLL server for recent log events via GetAdminLog."""
        import asyncio as _asyncio
        try:
            raw = await _asyncio.wait_for(
                send_command("GetAdminLog", {"LogBackTrackTime": 65}),
                timeout=15.0,
            )
        except _asyncio.TimeoutError:
            logger.warning("GetAdminLog timed out after 15s")
            return []
        except Exception as e:
            logger.warning("Failed to get HLL logs: %s", e)
            return []

        if not raw or (isinstance(raw, str) and raw.startswith("Error")):
            return []

        now = datetime.now(timezone.utc)
        events = []

        # Handle GetAdminLog response: {"entries": [{"timestamp": "...", "message": "..."}]}
        # or JSON array or newline-separated log lines
        lines: list[str] = []
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict) and "entries" in parsed:
                # GetAdminLog format: extract message strings
                lines = [e.get("message", "") for e in parsed["entries"] if e.get("message")]
            elif isinstance(parsed, list):
                lines = [str(entry) for entry in parsed]
            elif isinstance(parsed, str):
                lines = parsed.splitlines()
            else:
                lines = str(raw).splitlines()
        except (json.JSONDecodeError, TypeError):
            lines = str(raw).splitlines()

        for line in lines:
            event = self._parse_log_line(line, now)
            if event:
                events.append(event)

        return events
