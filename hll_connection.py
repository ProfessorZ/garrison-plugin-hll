"""HLL RCON protocol — plain text over TCP with XOR encryption.

The actual HLL game server RCON protocol:
1. TCP connect
2. Server immediately sends XOR key (raw bytes, no framing)
3. XOR-encrypt ALL subsequent sends and decrypt ALL received bytes
4. Send: "login <password>\n" → expect "SUCCESS" or "FAIL"
5. Commands are plain strings, separated by spaces/newlines
6. Lists are tab-separated: "<count>\\t<item1>\\t<item2>\\t"
7. Responses are: SUCCESS, FAIL, EMPTY, or a data string

Reference: https://gist.github.com/timraay/5634d85eab552b5dfafb9fd61273dc52
"""

import array
import asyncio
import logging

logger = logging.getLogger(__name__)

XOR_KEY_LENGTH = 64  # Key length sent by server on connect


class HLLAuthError(Exception):
    pass


class HLLCommandError(Exception):
    pass


class HLLConnection:
    """Async TCP connection to a Hell Let Loose RCON server."""

    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self._xorkey: bytes | None = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect, receive XOR key, and authenticate."""
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=10,
        )
        # Step 1: Server sends the XOR key immediately on connect (raw bytes)
        self._xorkey = await asyncio.wait_for(
            self.reader.read(XOR_KEY_LENGTH),
            timeout=5,
        )
        logger.debug("HLL XOR key received (%d bytes)", len(self._xorkey))

        # Step 2: Login
        resp = await self._send("login %s" % self.password)
        if resp.strip() != "SUCCESS":
            raise HLLAuthError("HLL login failed (bad password?)")
        logger.info("HLL RCON authenticated to %s:%d", self.host, self.port)

    async def send(self, command: str) -> str:
        """Send a command and return the plain text response."""
        async with self._lock:
            return await self._send(command)

    async def close(self) -> None:
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None
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

    async def _send(self, command: str) -> str:
        """Internal: send command (already holds lock or is pre-auth)."""
        payload = self._xor(command.encode("utf-8"))
        # Prefix with 4-byte little-endian length
        import struct
        length_prefix = struct.pack("<I", len(payload))
        self.writer.write(length_prefix + payload)
        await self.writer.drain()
        return await self._receive()

    async def _receive(self) -> str:
        """Read a length-prefixed XOR-encrypted response."""
        import struct
        # Read 4-byte length prefix
        length_bytes = await asyncio.wait_for(self.reader.readexactly(4), timeout=15)
        length = struct.unpack("<I", length_bytes)[0]
        # Read the response body
        raw = await asyncio.wait_for(self.reader.readexactly(length), timeout=15)
        return self._xor(raw).decode("utf-8", errors="replace")

    @staticmethod
    def parse_list(response: str) -> list[str]:
        """Parse a tab-separated HLL list: '<count>\\t<item1>\\t<item2>\\t'"""
        if not response or response.strip() in ("EMPTY", "FAIL"):
            return []
        parts = response.split("\t")
        if not parts:
            return []
        try:
            count = int(parts[0])
            return [p for p in parts[1:count + 1] if p]
        except (ValueError, IndexError):
            # Fallback: just split on tabs and filter empty
            return [p for p in parts if p.strip()]
