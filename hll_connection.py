"""HLL custom JSON-over-TCP RCON protocol implementation."""

import asyncio
import json
import logging
import struct

HEADER_FORMAT = "<II"
HEADER_SIZE = 8

logger = logging.getLogger(__name__)


class HLLConnection:
    """Manages a TCP connection to a Hell Let Loose RCON server."""

    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.auth_token: str | None = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._request_id = 0
        self._lock = asyncio.Lock()

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def connect(self) -> None:
        """Connect to the server and authenticate."""
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=10,
        )
        # Authenticate
        resp = await self._send_raw(
            self._next_request_id(),
            "Login",
            version=1,
            content=json.dumps({"password": self.password}),
        )
        status = resp.get("statusCode", 0)
        if status != 200:
            msg = resp.get("statusMessage", "Unknown error")
            raise ConnectionError(f"HLL authentication failed: {msg}")
        # Extract auth token from contentBody
        content_body = resp.get("contentBody", "")
        if isinstance(content_body, str):
            try:
                content_body = json.loads(content_body)
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(content_body, dict):
            self.auth_token = content_body.get("token", content_body.get("authToken", ""))
        else:
            self.auth_token = str(content_body)
        logger.info("HLL RCON authenticated to %s:%d", self.host, self.port)

    async def send(self, command: str, version: int = 1, content: str = "") -> dict:
        """Send a command and return the parsed response dict."""
        async with self._lock:
            return await self._send_raw(self._next_request_id(), command, version, content)

    async def close(self) -> None:
        """Close the TCP connection."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None
        self.auth_token = None

    @property
    def connected(self) -> bool:
        return self.writer is not None and not self.writer.is_closing()

    async def _send_raw(self, request_id: int, command: str, version: int, content: str) -> dict:
        body = json.dumps({
            "authToken": self.auth_token or "",
            "version": version,
            "name": command,
            "contentBody": content,
        }).encode("utf-8")
        header = struct.pack(HEADER_FORMAT, request_id, len(body))
        self.writer.write(header + body)
        await self.writer.drain()
        return await self._receive_raw(request_id)

    async def _receive_raw(self, expected_request_id: int) -> dict:
        header = await asyncio.wait_for(
            self.reader.readexactly(HEADER_SIZE),
            timeout=15,
        )
        req_id, body_len = struct.unpack(HEADER_FORMAT, header)
        body = await asyncio.wait_for(
            self.reader.readexactly(body_len),
            timeout=15,
        )
        return json.loads(body)
