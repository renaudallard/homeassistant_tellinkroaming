"""Tellink API handler — WebSocket communication with mytellink.com."""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

SSL_CONTEXT = ssl.create_default_context()

_LOGGER = logging.getLogger(__name__)


class TellinkError(Exception):
    """Base error for the Tellink portal."""


class TellinkConnectionError(TellinkError):
    """The portal could not be reached."""


class TellinkAuthError(TellinkError):
    """The portal did not return a session for these credentials."""


class TellinkAPI:
    """Handle communication with the Tellink prepaid portal via WebSocket."""

    URL = "wss://www.mytellink.com/prepaid/"

    # A login is a handful of frames; anything longer is a stuck connection.
    TOTAL_TIMEOUT = 30

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    async def get_data(self) -> dict:
        """Login through WebSocket and parse the SessionCli JSON.

        Raises TellinkConnectionError if the portal cannot be reached and
        TellinkAuthError if it never returns a session for these credentials.
        """
        _LOGGER.debug("[%s] Connecting to %s", self.username, self.URL)

        try:
            async with asyncio.timeout(self.TOTAL_TIMEOUT):
                return await self._login()
        except asyncio.TimeoutError as err:
            raise TellinkConnectionError(
                f"No session after {self.TOTAL_TIMEOUT} s"
            ) from err

    async def _login(self) -> dict:
        """Open the socket, send the credentials and wait for the session."""
        # The portal refuses a login by closing the socket rather than by
        # sending an error frame, so the same close means different things
        # before and after the credentials go out.
        sent_credentials = False
        try:
            async with websockets.connect(
                self.URL,
                ssl=SSL_CONTEXT,
                max_size=2**20,
                ping_interval=None,
                close_timeout=5,
            ) as ws:
                # Wait for Challenge
                try:
                    challenge_msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    _LOGGER.debug(
                        "[%s] Received challenge: %s", self.username, challenge_msg
                    )
                except asyncio.TimeoutError as err:
                    raise TellinkConnectionError(
                        "Timed out waiting for the challenge"
                    ) from err

                # Send credentials
                cred = {
                    "tag": "Credentials",
                    "username": self.username,
                    "password": self.password,
                }
                await ws.send(json.dumps(cred))
                sent_credentials = True
                _LOGGER.debug("[%s] Sent credentials payload", self.username)

                # Wait for SessionCli
                for _ in range(20):
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    except asyncio.TimeoutError:
                        continue

                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        continue

                    if data.get("tag") == "SessionCli":
                        parsed = self._parse_session_cli(data)
                        if not parsed:
                            raise TellinkError("Could not parse the SessionCli payload")
                        return parsed

        except (ConnectionClosedError, WebSocketException, OSError) as err:
            if sent_credentials:
                raise TellinkAuthError(
                    f"Portal closed the session after the credentials: {err}"
                ) from err
            raise TellinkConnectionError(str(err) or type(err).__name__) from err

        # Stayed connected but never sent a session.
        raise TellinkAuthError("No session returned; the credentials were refused")

    def _parse_session_cli(self, data: dict) -> dict:
        """Extract balance, status, username, and expiry info."""
        try:
            contents = data.get("contents", [])
            if not contents or not isinstance(contents[0], dict):
                return {}

            cli = contents[0]
            balance = round(float(cli.get("wcliCredit", 0.0)), 2)
            status = cli.get("wcliStatus")
            username = cli.get("wcliUsername")
            validity_list = cli.get("wcliValidity") or []
            expiry = validity_list[-1] if validity_list else None

            expiry_str = None
            if expiry:
                try:
                    expiry_date = datetime.fromisoformat(expiry).date()
                    expiry_str = expiry_date.isoformat()
                except (TypeError, ValueError):
                    expiry_str = expiry

            return {
                "balance": balance,
                "status": status,
                "username": username,
                "expiry": expiry_str,
            }
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("[%s] Error parsing SessionCli: %s", self.username, err)
            return {}
