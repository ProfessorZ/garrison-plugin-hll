"""Hell Let Loose server options handler."""

from app.plugins.base import ServerOption

# Maps HLL setting names to their getter command, setter command, and metadata.
HLL_OPTIONS = [
    {
        "name": "VoteKickEnabled",
        "getter": "GetVoteKickEnabled",
        "setter": "SetVoteKickEnabled",
        "type": "boolean",
        "category": "Moderation",
        "description": "Allow players to vote-kick others",
    },
    {
        "name": "AutoBalanceEnabled",
        "getter": "GetAutoBalanceEnabled",
        "setter": "SetAutoBalanceEnabled",
        "type": "boolean",
        "category": "Gameplay",
        "description": "Automatically balance teams",
    },
    {
        "name": "AutoBalanceThreshold",
        "getter": "GetAutoBalanceThreshold",
        "setter": "SetAutoBalanceThreshold",
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
        "type": "boolean",
        "category": "Moderation",
        "description": "Filter profanity in chat messages",
    },
]

# Lookup by option name for set_option
_OPTIONS_BY_NAME = {opt["name"]: opt for opt in HLL_OPTIONS}


async def fetch_options(send_command) -> list[ServerOption]:
    """Fetch all HLL server options by issuing getter commands.

    HLL RCON returns plain-text values (e.g. "on", "off", "30").
    """
    options: list[ServerOption] = []
    for opt in HLL_OPTIONS:
        try:
            value = await send_command(opt["getter"])
            options.append(ServerOption(
                name=opt["name"],
                value=value.strip(),
                option_type=opt["type"],
                category=opt["category"],
                description=opt["description"],
                min_val=opt.get("min_val"),
                max_val=opt.get("max_val"),
            ))
        except Exception:
            pass
    return options


async def set_option(send_command, name: str, value: str) -> str:
    """Set an HLL server option by name.

    HLL setter commands take the value as an argument, e.g.:
        SetAutoBalanceThreshold 3
    """
    opt = _OPTIONS_BY_NAME.get(name)
    if not opt:
        raise ValueError(f"Unknown HLL option: {name}")
    result = await send_command(opt["setter"], value)
    if result.upper().startswith("SUCCESS") or result.upper() == "PASS":
        return f"{name} set to {value}"
    return f"Failed to set {name}: {result}"
