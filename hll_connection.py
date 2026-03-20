"""HLL RCON protocol: JSON bodies, XOR-encrypted, with binary-framed headers."""

import asyncio
import base64
import json
import logging
import struct

logger = logging.getLogger(__name__)


def _xor(data: bytes, key: bytes) -> bytes:
    """XOR each byte of *data* with *key* (cycling)."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


class HLLConnection:
    """Async TCP connection to a Hell Let Loose RCON server."""

    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._xor_key: bytes | None = None
        self._auth_token: str = ""
        self._request_id: int = 0
        self._lock = asyncio.Lock()

    # ── public API ────────────────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> None:
        """Connect, handshake for XOR key, and authenticate."""
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=10,
        )

        # Step 1 — ServerConnect (unencrypted) to get XOR key.
        resp = await self._send_raw("ServerConnect", "")
        xor_key_b64 = resp.get("contentBody", "")
        self._xor_key = base64.b64decode(xor_key_b64)
        logger.debug("Received XOR key: %s (%d bytes)", self._xor_key.hex(), len(self._xor_key))

        # Step 2 — Login with password (now XOR-encrypted).
        resp = await self._send_raw("Login", self.password)
        if resp.get("statusCode") != 200:
            await self.close()
            raise ConnectionError(
                f"HLL authentication failed: {resp.get('statusMessage', 'unknown error')}"
            )
        self._auth_token = resp.get("contentBody", "")
        logger.info("HLL RCON authenticated to %s:%d", self.host, self.port)

    async def send(self, command: str, content: str | dict = "") -> str:
        """Send a command and return the contentBody of the response.

        If *content* is a dict it is JSON-encoded before being placed in the
        request's ``contentBody`` field.
        """
        if isinstance(content, dict):
            content = json.dumps(content)
        async with self._lock:
            resp = await self._send_raw(command, content)
            return resp.get("contentBody", "")

    async def close(self) -> None:
        """Close the TCP connection."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    # ── internals ─────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _send_raw(self, command: str, content: str) -> dict:
        """Build, send, and receive a single request/response pair."""
        body_obj = {
            "authToken": self._auth_token,
            "version": 2,
            "name": command,
            "contentBody": content,
        }
        body_bytes = json.dumps(body_obj).encode("utf-8")

        if self._xor_key is not None:
            body_bytes = _xor(body_bytes, self._xor_key)

        request_id = self._next_id()
        header = struct.pack("<II", request_id, len(body_bytes))
        self._writer.write(header + body_bytes)
        await self._writer.drain()

        return await self._read_response()

    async def _read_response(self) -> dict:
        """Read one framed response: 8-byte header then body."""
        header = await asyncio.wait_for(self._reader.readexactly(8), timeout=30)
        _resp_id, body_len = struct.unpack("<II", header)

        body_bytes = await asyncio.wait_for(self._reader.readexactly(body_len), timeout=30)

        if self._xor_key is not None:
            body_bytes = _xor(body_bytes, self._xor_key)

        try:
            return json.loads(body_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Failed to parse response body: %s", exc)
            return {"contentBody": body_bytes.decode("utf-8", errors="replace")}
