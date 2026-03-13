"""HLL RCON protocol — custom JSON-over-TCP with XOR encryption.

Protocol summary:
1. TCP connect
2. Server sends ServerConnect (v2) response with base64-encoded XOR key in contentBody
3. XOR key is applied to ALL subsequent message bodies (both send and receive)
4. Send Login (v2) with raw password string as contentBody → response contentBody is the auth token
5. Use auth token in all subsequent requests

Reference: https://github.com/MarechJ/hll_rcon_tool
"""

import array
import asyncio
import base64
import itertools
import json
import logging
import struct

HEADER_FORMAT = "<II"
HEADER_SIZE = 8

logger = logging.getLogger(__name__)


class HLLAuthError(Exception):
    pass


class HLLCommandError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"({status_code}) {message}")


class HLLConnection:
    """Async TCP connection to a Hell Let Loose RCON server."""

    _id_counter = itertools.count(start=1)

    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.auth_token: str | None = None
        self._xorkey: bytes | None = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect, perform ServerConnect handshake, then Login."""
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=10,
        )

        # Step 1: ServerConnect — server sends us the XOR key
        hello = await self._exchange_raw("ServerConnect", version=2, content="")
        if hello.get("statusCode", 0) != 200:
            raise HLLAuthError(f"ServerConnect failed: {hello.get('statusMessage')}")
        xorkey_b64 = hello.get("contentBody", "")
        if xorkey_b64:
            self._xorkey = base64.b64decode(xorkey_b64)
        logger.debug("HLL XOR key received (%d bytes)", len(self._xorkey) if self._xorkey else 0)

        # Step 2: Login — send password as plain string, get auth token back
        auth = await self._exchange_raw("Login", version=2, content=self.password)
        if auth.get("statusCode", 0) != 200:
            raise HLLAuthError(f"HLL login failed: {auth.get('statusMessage', 'bad password?')}")
        self.auth_token = auth.get("contentBody", "")
        logger.info("HLL RCON authenticated to %s:%d", self.host, self.port)

    async def send(self, command: str, version: int = 1, content: str | dict = "") -> dict:
        """Send a command, return parsed response dict. Thread-safe."""
        if isinstance(content, dict):
            content = json.dumps(content, separators=(",", ":"))
        async with self._lock:
            resp = await self._exchange_raw(command, version=version, content=content)
        if resp.get("statusCode", 200) >= 500:
            raise HLLCommandError(resp["statusCode"], resp.get("statusMessage", ""))
        return resp

    async def close(self) -> None:
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None
        self.auth_token = None
        self._xorkey = None

    @property
    def connected(self) -> bool:
        return self.writer is not None and not self.writer.is_closing()

    def _xor(self, data: bytes) -> bytes:
        """XOR-encrypt/decrypt data with the server key."""
        if not self._xorkey:
            return data
        key = self._xorkey
        return array.array("B", [data[i] ^ key[i % len(key)] for i in range(len(data))]).tobytes()

    async def _exchange_raw(self, command: str, version: int, content: str) -> dict:
        request_id = next(self._id_counter)
        body_dict = {
            "authToken": self.auth_token or "",
            "version": version,
            "name": command,
            "contentBody": content,
        }
        body_bytes = json.dumps(body_dict, separators=(",", ":")).encode("utf-8")
        # XOR the body (not the header)
        body_bytes = self._xor(body_bytes)
        header = struct.pack(HEADER_FORMAT, request_id, len(body_bytes))
        self.writer.write(header + body_bytes)
        await self.writer.drain()

        # Read response
        resp_header = await asyncio.wait_for(self.reader.readexactly(HEADER_SIZE), timeout=15)
        _, resp_body_len = struct.unpack(HEADER_FORMAT, resp_header)
        resp_body = await asyncio.wait_for(self.reader.readexactly(resp_body_len), timeout=15)
        # XOR-decrypt response body
        resp_body = self._xor(resp_body)
        return json.loads(resp_body)
