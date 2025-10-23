# 202510231200
"""Tellink API handler — WebSocket communication with mytellink.com."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

_LOGGER = logging.getLogger(__name__)


class TellinkAPI:
    """Handle communication with the Tellink prepaid portal via WebSocket."""

    URL = "wss://www.mytellink.com/prepaid/"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    async def get_data(self) -> dict:
        """Login through WebSocket and parse the SessionCli JSON."""
        _LOGGER.debug("[%s] Connecting to %s", self.username, self.URL)

        try:
            async with websockets.connect(
                self.URL,
                max_size=2**20,
                ping_interval=None,
                close_timeout=5,
            ) as ws:
                # Wait for Challenge
                try:
                    challenge_msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    _LOGGER.debug("[%s] Received challenge: %s", self.username, challenge_msg)
                except asyncio.TimeoutError:
                    _LOGGER.warning("[%s] Timeout waiting for challenge", self.username)
                    return {}

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

                    if data.get("tag") == "SessionCli":
                        return self._parse_session_cli(data)

        except (ConnectionClosedError, WebSocketException) as err:
            _LOGGER.error("[%s] WebSocket error: %s", self.username, err)
        except Exception as err:
            _LOGGER.exception("[%s] Unexpected error: %s", self.username, err)

        _LOGGER.warning("[%s] Did not receive valid SessionCli JSON", self.username)
        return {}

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
                except Exception:
                    expiry_str = expiry

            return {
                "balance": balance,
                "status": status,
                "username": username,
                "expiry": expiry_str,
            }
        except Exception as err:
            _LOGGER.warning("[%s] Error parsing SessionCli: %s", self.username, err)
            return {}
