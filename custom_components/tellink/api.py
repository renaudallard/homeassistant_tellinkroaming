"""Tellink API handler — WebSocket communication with mytellink.com."""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from datetime import datetime

import websockets
from websockets.exceptions import WebSocketException

SSL_CONTEXT = ssl.create_default_context()

_LOGGER = logging.getLogger(__name__)

# websockets logs every frame it sends at DEBUG, payload included, and the
# credentials frame carries the password in clear. Hand the connection a
# logger that will not emit it whatever the rest of the tree is set to.
_WS_LOGGER = logging.getLogger(f"{__name__}.websocket")
_WS_LOGGER.setLevel(logging.INFO)


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
        try:
            async with websockets.connect(
                self.URL,
                ssl=SSL_CONTEXT,
                max_size=2**20,
                ping_interval=None,
                close_timeout=5,
                logger=_WS_LOGGER,
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

                    if not isinstance(data, dict):
                        continue

                    tag = data.get("tag")

                    if tag == "SessionCli":
                        parsed = self._parse_session_cli(data)
                        if not parsed:
                            raise TellinkError("Could not parse the SessionCli payload")
                        return parsed

                    if tag == "Challenge":
                        # A second challenge is how the portal says no. Its own
                        # web client shows "Invalid credentials" when a
                        # challenge arrives after the login was submitted.
                        raise TellinkAuthError("The portal refused the credentials")

        except (WebSocketException, OSError) as err:
            # Every close, reset and socket error is a network problem. Calling
            # one of them a refused login would blame the password and stop the
            # coordinator for good, since Home Assistant does not reschedule
            # after an auth failure. The portal states a refusal explicitly.
            raise TellinkConnectionError(str(err) or type(err).__name__) from err

        # Neither a session nor a refusal inside the frame budget.
        raise TellinkConnectionError("No session returned within the frame budget")

    def _parse_session_cli(self, data: dict) -> dict:
        """Extract balance, status, username, and expiry info."""
        try:
            contents = data.get("contents", [])
            if not contents or not isinstance(contents[0], dict):
                return {}

            cli = contents[0]
            # No credit field at all is unknown, not zero: reporting zero fires
            # the low credit alerts and writes a false trough into statistics.
            raw_credit = cli.get("wcliCredit")
            balance = None if raw_credit is None else round(float(raw_credit), 2)
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
