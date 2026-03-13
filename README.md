# Garrison Plugin — Hell Let Loose

RCON plugin for **Hell Let Loose** dedicated servers. Uses the HLL-specific JSON-over-TCP RCON protocol (not Source RCON).

## Setup

### 1. Enable RCON on your HLL server

In your server's `Game.ini` or startup configuration, ensure RCON is enabled and a password is set. The RCON port is typically separate from the game port.

### 2. Default Ports

| Port | Default | Description |
|------|---------|-------------|
| Game | 7777 | Game server port |
| RCON | 27015 | RCON administration port |

### 3. Add server in Garrison

When adding an HLL server in Garrison, select **Hell Let Loose** as the game type and provide the RCON host, port, and password.

## Features

### Steam ID Tracking

HLL natively provides Steam64 IDs for all connected players via `GetPlayerIds`. Unlike some other games, no additional parsing or workarounds are needed — every player is identified by their Steam ID from the moment they connect.

### Available Commands

**Player Management:** GetPlayerIds, KickPlayerById, TempBanByPlayerId, PermanentBanByPlayerId, UnbanByPlayerId, GetBans, GetAdminIds, AddAdminById, RemoveAdminById

**Server Info:** GetServerName, GetSlots, GetGameState, GetCurrentMap, GetNextMap, GetMapRotation

**Map Management:** RotateMap, SetMap, AddMapToRotation, RemoveMapFromRotation

**Server Settings:** AutoBalance, TeamSwitchCooldown, IdleAutokick, MaxPingAutokick, VoteKick, HighPingLimit, ProfanityFilter (all have Get/Set pairs)

**Messaging:** Broadcast

**Logs:** GetStructuredLogs (joins, leaves, kills, chat)

### Server Options

The following options can be viewed and changed through Garrison's server options panel:

| Option | Type | Description |
|--------|------|-------------|
| VoteKickEnabled | Boolean | Allow players to vote-kick |
| AutoBalanceEnabled | Boolean | Auto-balance teams |
| AutoBalanceThreshold | Integer | Player difference before auto-balance |
| TeamSwitchCooldown | Integer | Minutes before team switch allowed |
| IdleAutokickTime | Integer | Idle minutes before kick (0 = off) |
| MaxPingAutokick | Integer | Max ping in ms (0 = off) |
| HighPingLimit | Integer | High ping warning limit in ms |
| ProfanityFilterEnabled | Boolean | Filter chat profanity |

## Install

### Via Garrison UI

Install from the plugin marketplace or add the repository URL:

```
https://github.com/ProfessorZ/garrison-plugin-hll
```

### Manual

Clone into your plugins directory:

```bash
cd /path/to/garrison/plugins
git clone https://github.com/ProfessorZ/garrison-plugin-hll garrison-plugin-hll
```

Restart Garrison to load the plugin.

## Protocol Notes

HLL uses a custom JSON-over-TCP protocol, not Source RCON. This plugin implements its own TCP connection handler (`hll_connection.py`) with:

- 8-byte little-endian header (request_id + body_length)
- JSON request/response bodies
- Token-based authentication (Login command returns auth token)
- All subsequent commands include the auth token

The plugin sets `custom_connection = True` so Garrison routes through the HLL protocol instead of the shared Source RCON manager.
