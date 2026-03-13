"""Garrison plugin for Hell Let Loose dedicated servers.

HLL RCON uses plain text commands over XOR-encrypted TCP.
Commands: "get players", "kick <name> <reason>", etc.
Lists are tab-separated: "<count>\\t<item1>\\t<item2>\\t"
"""

import logging
from typing import Callable, Awaitable

from app.plugins.base import (
    CommandDef,
    CommandParam,
    GamePlugin,
    PlayerInfo,
    ServerOption,
    ServerStatus,
)
from hll_connection import HLLConnection

logger = logging.getLogger(__name__)

# Type alias for the send_command callable passed by Garrison
SendCommand = Callable[[str], Awaitable[str]]


class HLLPlugin(GamePlugin):
    """Hell Let Loose RCON plugin."""

    custom_connection = True

    def __init__(self):
        self._connections: dict[str, HLLConnection] = {}

    @property
    def game_type(self) -> str:
        return "hll"

    @property
    def display_name(self) -> str:
        return "Hell Let Loose"

    # ── Custom connection lifecycle ──────────────────────────────────

    async def connect_custom(self, host: str, port: int, password: str) -> None:
        key = f"{host}:{port}"
        if key in self._connections:
            await self._connections[key].close()
        conn = HLLConnection(host, port, password)
        await conn.connect()
        self._connections[key] = conn

    async def disconnect_custom(self, host: str = None, port: int = None) -> None:
        if host and port:
            key = f"{host}:{port}"
            if key in self._connections:
                await self._connections[key].close()
                del self._connections[key]
        else:
            for conn in self._connections.values():
                await conn.close()
            self._connections.clear()

    async def send_command_custom(self, command: str, host: str = None, port: int = None) -> str:
        """Send a plain text HLL command, returns response string."""
        key = f"{host}:{port}" if host and port else next(iter(self._connections), None)
        if not key or key not in self._connections:
            return "FAIL"
        return await self._connections[key].send(command)

    # ── GamePlugin interface ─────────────────────────────────────────

    async def parse_players(self, raw_response: str) -> list[PlayerInfo]:
        """Parse 'get playerids' response: 'count\\tName : UID\\t...'"""
        items = HLLConnection.parse_list(raw_response)
        players = []
        for item in items:
            if " : " in item:
                name, uid = item.rsplit(" : ", 1)
                players.append(PlayerInfo(name=name.strip(), steam_id=uid.strip()))
            else:
                players.append(PlayerInfo(name=item.strip()))
        return players

    async def get_status(self, send_command: SendCommand) -> ServerStatus:
        try:
            slots_raw = await send_command("get slots")
            # "89/100"
            if "/" in slots_raw:
                current, maximum = slots_raw.strip().split("/")
                return ServerStatus(
                    online=True,
                    player_count=int(current.strip()),
                )
            return ServerStatus(online=True, player_count=0)
        except Exception as e:
            logger.warning("HLL get_status failed: %s", e)
            return ServerStatus(online=False)

    async def get_players(self, send_command: SendCommand) -> list[PlayerInfo]:
        raw = await send_command("get playerids")
        return await self.parse_players(raw)

    async def get_options(self, send_command: SendCommand) -> list[ServerOption]:
        options = []
        settings = {
            "get autobalanceenabled": ("AutoBalance", "boolean", "Automatically balance teams"),
            "get autobalancethreshold": ("AutoBalance Threshold", "integer", "Max team size difference before autobalance kicks in"),
            "get votekickenabled": ("Vote Kick", "boolean", "Allow players to vote-kick other players"),
            "get teamSwitchCooldown": ("Team Switch Cooldown", "integer", "Cooldown in minutes before a player can switch teams"),
            "get idleautokicktime": ("Idle Autokick", "integer", "Minutes of inactivity before a player is kicked"),
            "get maxping": ("Max Ping Autokick", "integer", "Max ping in ms before autokick (0 = disabled)"),
            "get highping": ("High Ping Threshold", "integer", "High ping warning threshold in ms"),
            "get profanityfilter": ("Profanity Filter", "boolean", "Filter profanity in chat"),
        }
        for cmd, (name, opt_type, desc) in settings.items():
            try:
                val = await send_command(cmd)
                val = val.strip()
                if opt_type == "boolean":
                    # Responses like "Enabled" / "Disabled" or "TRUE" / "FALSE"
                    val = str(val.lower() in ("enabled", "true", "1", "on")).lower()
                options.append(ServerOption(
                    name=name,
                    value=val,
                    option_type=opt_type,
                    category="Server Settings",
                    description=desc,
                ))
            except Exception:
                pass
        return options

    async def set_option(self, send_command: SendCommand, name: str, value: str) -> str:
        mapping = {
            "AutoBalance": ("setautobalanceenabled", "boolean"),
            "AutoBalance Threshold": ("setautobalancethreshold", "integer"),
            "Vote Kick": ("setvotekickenabled", "boolean"),
            "Team Switch Cooldown": ("setteamswitchcooldown", "integer"),
            "Idle Autokick": ("setidleautokicktime", "integer"),
            "Max Ping Autokick": ("setmaxping", "integer"),
            "High Ping Threshold": ("sethighping", "integer"),
            "Profanity Filter": ("setprofanityfilter", "boolean"),
        }
        if name not in mapping:
            return f"Unknown option: {name}"
        cmd_name, opt_type = mapping[name]
        if opt_type == "boolean":
            v = "true" if value.lower() in ("true", "1", "on", "enabled") else "false"
        else:
            v = value
        return await send_command(f"{cmd_name} {v}")

    async def kick_player(self, send_command: SendCommand, name: str, reason: str = "") -> str:
        # Replace tabs in name/reason to prevent list injection
        name = name.replace("\t", " ")
        reason = reason.replace("\t", " ") if reason else "Kicked by admin"
        return await send_command(f'kick "{name}" "{reason}"')

    async def ban_player(self, send_command: SendCommand, name: str, reason: str = "") -> str:
        name = name.replace("\t", " ")
        reason = reason.replace("\t", " ") if reason else "Banned by admin"
        # Permanent ban by name (perma ban requires name, not UID unless we look it up)
        return await send_command(f'permaban "{name}" "{reason}"')

    async def unban_player(self, send_command: SendCommand, name: str) -> str:
        return await send_command(f'unban "{name}"')

    def format_command(self, command: str) -> str:
        return command  # HLL commands need no prefix

    def get_commands(self) -> list[CommandDef]:
        from .schema import HLL_COMMANDS
        return HLL_COMMANDS
