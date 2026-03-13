"""Hell Let Loose server options handler."""

import json

from app.plugins.base import ServerOption

# Maps HLL setting names to their getter command, setter command, and metadata.
HLL_OPTIONS = [
    {
        "name": "VoteKickEnabled",
        "getter": "GetVoteKickEnabled",
        "setter": "SetVoteKickEnabled",
        "content_key": "enabled",
        "type": "boolean",
        "category": "Moderation",
        "description": "Allow players to vote-kick others",
    },
    {
        "name": "AutoBalanceEnabled",
        "getter": "GetAutoBalanceEnabled",
        "setter": "SetAutoBalanceEnabled",
        "content_key": "enabled",
        "type": "boolean",
        "category": "Gameplay",
        "description": "Automatically balance teams",
    },
    {
        "name": "AutoBalanceThreshold",
        "getter": "GetAutoBalanceThreshold",
        "setter": "SetAutoBalanceThreshold",
        "content_key": "threshold",
        "type": "integer",
        "category": "Gameplay",
        "description": "Player difference threshold before auto-balance triggers",
        "min_val": 0,
        "max_val": 50,
    },
    {
        "name": "TeamSwitchCooldown",
        "getter": "GetTeamSwitchCooldown",
        "setter": "SetTeamSwitchCooldown",
        "content_key": "cooldown",
        "type": "integer",
        "category": "Gameplay",
        "description": "Cooldown in minutes before a player can switch teams again",
        "min_val": 0,
        "max_val": 60,
    },
    {
        "name": "IdleAutokickTime",
        "getter": "GetIdleAutokickTime",
        "setter": "SetIdleAutokickTime",
        "content_key": "minutes",
        "type": "integer",
        "category": "Server",
        "description": "Minutes of inactivity before a player is kicked (0 = disabled)",
        "min_val": 0,
        "max_val": 120,
    },
    {
        "name": "MaxPingAutokick",
        "getter": "GetMaxPingAutokick",
        "setter": "SetMaxPingAutokick",
        "content_key": "max_ping",
        "type": "integer",
        "category": "Server",
        "description": "Maximum ping in ms before auto-kick (0 = disabled)",
        "min_val": 0,
        "max_val": 2000,
    },
    {
        "name": "HighPingLimit",
        "getter": "GetHighPingLimit",
        "setter": "SetHighPingLimit",
        "content_key": "limit",
        "type": "integer",
        "category": "Server",
        "description": "High ping warning limit in milliseconds",
        "min_val": 0,
        "max_val": 2000,
    },
    {
        "name": "ProfanityFilterEnabled",
        "getter": "GetProfanityFilterEnabled",
        "setter": "SetProfanityFilterEnabled",
        "content_key": "enabled",
        "type": "boolean",
        "category": "Moderation",
        "description": "Filter profanity in chat messages",
    },
]

# Lookup by option name for set_option
_OPTIONS_BY_NAME = {opt["name"]: opt for opt in HLL_OPTIONS}


async def fetch_options(send_command) -> list[ServerOption]:
    """Fetch all HLL server options by issuing getter commands."""
    options: list[ServerOption] = []
    for opt in HLL_OPTIONS:
        try:
            raw = await send_command(opt["getter"])
            data = json.loads(raw) if isinstance(raw, str) else raw
            content = data.get("contentBody", "")
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    pass
            # Extract value
            if isinstance(content, dict):
                value = str(content.get(opt["content_key"], content.get("value", "")))
            else:
                value = str(content)
            options.append(ServerOption(
                name=opt["name"],
                value=value,
                option_type=opt["type"],
                category=opt["category"],
                description=opt["description"],
                min_val=opt.get("min_val"),
                max_val=opt.get("max_val"),
            ))
        except Exception:
            # Skip options that fail to fetch
            pass
    return options


async def set_option(send_command, name: str, value: str) -> str:
    """Set an HLL server option by name."""
    opt = _OPTIONS_BY_NAME.get(name)
    if not opt:
        raise ValueError(f"Unknown HLL option: {name}")
    # Coerce value to the right type for the JSON content
    if opt["type"] == "boolean":
        coerced = value.lower() in ("true", "1", "yes")
        content = json.dumps({opt["content_key"]: coerced})
    elif opt["type"] == "integer":
        content = json.dumps({opt["content_key"]: int(value)})
    else:
        content = json.dumps({opt["content_key"]: value})
    raw = await send_command(f'{opt["setter"]} {content}')
    data = json.loads(raw) if isinstance(raw, str) else raw
    status = data.get("statusCode", 0)
    if status == 200:
        return f"{name} set to {value}"
    return f"Failed to set {name}: {data.get('statusMessage', 'unknown error')}"
