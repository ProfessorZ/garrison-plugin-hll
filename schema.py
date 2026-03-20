"""Hell Let Loose RCON command schema v2.0.0 — GetServerInformation API."""


def get_commands():
    """Return the list of CommandDef objects for Hell Let Loose."""
    from app.plugins.base import CommandDef, CommandParam

    return [
        # ── SERVER INFORMATION ─────────────────────────────────────────
        CommandDef(
            name="GetServerInformation",
            description="Query server information by Name parameter (session, players, slots, etc.)",
            category="SERVER",
            params=[
                CommandParam(
                    name="Name",
                    type="string",
                    description="Information type: session, players, slots",
                    choices=["session", "players", "slots"],
                ),
                CommandParam(
                    name="Value",
                    type="string",
                    required=False,
                    description="Optional value filter (usually empty string)",
                    default="",
                ),
            ],
            example='GetServerInformation {"Name": "session", "Value": ""}',
        ),

        # ── PLAYER MANAGEMENT ─────────────────────────────────────────
        CommandDef(
            name="KickPlayerById",
            description="Kick a player by Steam ID",
            category="MODERATION",
            params=[
                CommandParam(name="player_id", type="string", description="Player Steam64 ID"),
                CommandParam(name="reason", type="string", required=False, description="Kick reason"),
            ],
            admin_only=True,
            example='KickPlayerById {"player_id": "76561198...", "reason": "AFK"}',
        ),
        CommandDef(
            name="TempBanByPlayerId",
            description="Temporarily ban a player",
            category="MODERATION",
            params=[
                CommandParam(name="player_id", type="string", description="Player Steam64 ID"),
                CommandParam(name="duration_hours", type="integer", description="Ban duration in hours"),
                CommandParam(name="reason", type="string", required=False, description="Ban reason"),
                CommandParam(name="by_admin_name", type="string", required=False, description="Admin who issued the ban"),
            ],
            admin_only=True,
            example='TempBanByPlayerId {"player_id": "76561198...", "duration_hours": 24, "reason": "TK"}',
        ),
        CommandDef(
            name="PermanentBanByPlayerId",
            description="Permanently ban a player",
            category="MODERATION",
            params=[
                CommandParam(name="player_id", type="string", description="Player Steam64 ID"),
                CommandParam(name="reason", type="string", required=False, description="Ban reason"),
                CommandParam(name="by_admin_name", type="string", required=False, description="Admin who issued the ban"),
            ],
            admin_only=True,
            example='PermanentBanByPlayerId {"player_id": "76561198...", "reason": "Cheating"}',
        ),
        CommandDef(
            name="UnbanByPlayerId",
            description="Unban a player by Steam ID",
            category="MODERATION",
            params=[
                CommandParam(name="player_id", type="string", description="Player Steam64 ID"),
            ],
            admin_only=True,
            example='UnbanByPlayerId {"player_id": "76561198..."}',
        ),
        CommandDef(
            name="GetBans",
            description="List all active bans",
            category="MODERATION",
            example="GetBans",
        ),
        CommandDef(
            name="GetAdminIds",
            description="List all admin Steam IDs",
            category="ADMIN",
            example="GetAdminIds",
        ),
        CommandDef(
            name="AddAdminById",
            description="Add an admin by Steam ID",
            category="ADMIN",
            params=[
                CommandParam(name="player_id", type="string", description="Steam64 ID to grant admin"),
            ],
            admin_only=True,
            example='AddAdminById {"player_id": "76561198..."}',
        ),
        CommandDef(
            name="RemoveAdminById",
            description="Remove an admin by Steam ID",
            category="ADMIN",
            params=[
                CommandParam(name="player_id", type="string", description="Steam64 ID to revoke admin"),
            ],
            admin_only=True,
            example='RemoveAdminById {"player_id": "76561198..."}',
        ),

        # ── MAP MANAGEMENT ────────────────────────────────────────────
        CommandDef(
            name="RotateMap",
            description="Advance to the next map in rotation",
            category="WORLD",
            admin_only=True,
            example="RotateMap",
        ),
        CommandDef(
            name="SetMap",
            description="Change to a specific map",
            category="WORLD",
            params=[
                CommandParam(name="map_name", type="string", description="Map name to switch to"),
            ],
            admin_only=True,
            example='SetMap {"map_name": "Carentan"}',
        ),
        CommandDef(
            name="AddMapToRotation",
            description="Add a map to the rotation",
            category="WORLD",
            params=[
                CommandParam(name="map_name", type="string", description="Map name to add"),
            ],
            admin_only=True,
            example='AddMapToRotation {"map_name": "Carentan"}',
        ),
        CommandDef(
            name="RemoveMapFromRotation",
            description="Remove a map from the rotation",
            category="WORLD",
            params=[
                CommandParam(name="map_name", type="string", description="Map name to remove"),
            ],
            admin_only=True,
            example='RemoveMapFromRotation {"map_name": "Carentan"}',
        ),

        # ── SERVER SETTINGS ───────────────────────────────────────────
        CommandDef(name="GetAutoBalanceEnabled", description="Check if auto-balance is enabled", category="SERVER", example="GetAutoBalanceEnabled"),
        CommandDef(
            name="SetAutoBalanceEnabled",
            description="Enable or disable auto-balance",
            category="SERVER",
            params=[CommandParam(name="enabled", type="boolean", description="Enable or disable")],
            admin_only=True,
            example='SetAutoBalanceEnabled {"enabled": true}',
        ),
        CommandDef(name="GetAutoBalanceThreshold", description="Get auto-balance threshold", category="SERVER", example="GetAutoBalanceThreshold"),
        CommandDef(
            name="SetAutoBalanceThreshold",
            description="Set auto-balance threshold",
            category="SERVER",
            params=[CommandParam(name="threshold", type="integer", description="Player count threshold")],
            admin_only=True,
            example='SetAutoBalanceThreshold {"threshold": 3}',
        ),
        CommandDef(name="GetTeamSwitchCooldown", description="Get team switch cooldown", category="SERVER", example="GetTeamSwitchCooldown"),
        CommandDef(
            name="SetTeamSwitchCooldown",
            description="Set team switch cooldown in minutes",
            category="SERVER",
            params=[CommandParam(name="cooldown", type="integer", description="Cooldown in minutes")],
            admin_only=True,
            example='SetTeamSwitchCooldown {"cooldown": 5}',
        ),
        CommandDef(name="GetIdleAutokickTime", description="Get idle autokick timeout", category="SERVER", example="GetIdleAutokickTime"),
        CommandDef(
            name="SetIdleAutokickTime",
            description="Set idle autokick time in minutes",
            category="SERVER",
            params=[CommandParam(name="minutes", type="integer", description="Idle timeout in minutes")],
            admin_only=True,
            example='SetIdleAutokickTime {"minutes": 10}',
        ),
        CommandDef(name="GetMaxPingAutokick", description="Get max ping autokick threshold", category="SERVER", example="GetMaxPingAutokick"),
        CommandDef(
            name="SetMaxPingAutokick",
            description="Set max ping autokick threshold in ms",
            category="SERVER",
            params=[CommandParam(name="max_ping", type="integer", description="Max ping in milliseconds")],
            admin_only=True,
            example='SetMaxPingAutokick {"max_ping": 500}',
        ),
        CommandDef(name="GetVoteKickEnabled", description="Check if vote kick is enabled", category="SERVER", example="GetVoteKickEnabled"),
        CommandDef(
            name="SetVoteKickEnabled",
            description="Enable or disable vote kick",
            category="SERVER",
            params=[CommandParam(name="enabled", type="boolean", description="Enable or disable")],
            admin_only=True,
            example='SetVoteKickEnabled {"enabled": true}',
        ),
        CommandDef(name="GetHighPingLimit", description="Get high ping limit", category="SERVER", example="GetHighPingLimit"),
        CommandDef(
            name="SetHighPingLimit",
            description="Set high ping limit in ms",
            category="SERVER",
            params=[CommandParam(name="limit", type="integer", description="Ping limit in milliseconds")],
            admin_only=True,
            example='SetHighPingLimit {"limit": 300}',
        ),
        CommandDef(name="GetProfanityFilterEnabled", description="Check if profanity filter is enabled", category="SERVER", example="GetProfanityFilterEnabled"),
        CommandDef(
            name="SetProfanityFilterEnabled",
            description="Enable or disable profanity filter",
            category="SERVER",
            params=[CommandParam(name="enabled", type="boolean", description="Enable or disable")],
            admin_only=True,
            example='SetProfanityFilterEnabled {"enabled": true}',
        ),

        # ── MESSAGING ─────────────────────────────────────────────────
        CommandDef(
            name="Broadcast",
            description="Broadcast a message to all players",
            category="SERVER",
            params=[
                CommandParam(name="message", type="string", description="Message to broadcast"),
            ],
            admin_only=True,
            example='Broadcast {"message": "Server restarting in 5 minutes"}',
        ),

        # ── LOGS ──────────────────────────────────────────────────────
        CommandDef(
            name="GetStructuredLogs",
            description="Get server logs (joins, leaves, kills, chat)",
            category="SERVER",
            example="GetStructuredLogs",
        ),
    ]
