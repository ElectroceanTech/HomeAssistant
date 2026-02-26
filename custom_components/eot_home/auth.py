"""EOT HOME Authentication Handler - Public Client Version."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed
from .const import API_URL,LOGGER





class EOTAuthHandler:
    """Handle EOT authentication using login -> authCode -> Cognito tokens."""

    def __init__(self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> None:
        """Initialize auth handler with user credentials.
        
        Args:
            session: aiohttp client session
            username: User's EOT username (unique per user)
            password: User's EOT password (unique per user)
        """
        self.session = session

        self.username = username
        self.password = password

        self.cognito_client_id = "f9752u6c156kopbpd058fipeg"
        self.cognito_redirect_uri = "https://d84l1y8p4kdic.cloudfront.net"
        self.cognito_token_url = "https://eotskill.auth.ap-south-1.amazoncognito.com/oauth2/token"
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: datetime | None = None

        self._lock = asyncio.Lock()

    async def async_get_access_token(self) -> str:
        """Return valid access token, refresh if needed."""
        async with self._lock:
            if self._is_token_valid():
                return self._access_token  # type: ignore

            # Try refresh token first
            if self._refresh_token:
                try:
                    await self._async_refresh_token()
                    return self._access_token  # type: ignore
                except Exception as err:
                    LOGGER.warning("Refresh failed, doing fresh login: %s", err)

            # Login again
            await self._async_authenticate()
            return self._access_token  # type: ignore

    def get_auth_headers(self) -> dict[str, str]:
        """Get API headers with bearer token."""
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}
    def get_access_token_sync(self, loop):
      """Synchronous method to get token from a thread"""
      future = asyncio.run_coroutine_threadsafe(
        self.async_get_access_token(),
        loop
      )
      return future.result()
    
    async def async_validate_auth(self) -> bool:
        """Validate current credentials."""
        try:
            await self.async_get_access_token()
            return True
        except Exception as err:
            return False


    def _is_token_valid(self) -> bool:
        """Check token validity with 5 min safety buffer."""
        if not self._access_token or not self._token_expires_at:
            return False
        return datetime.utcnow() < (self._token_expires_at - timedelta(minutes=5))

    async def _async_authenticate(self) -> None:
       """Perform full authentication flow to get tokens."""
       token_data = await self._async_login_get_tokens()
       self._update_tokens(token_data)


    async def _async_login_get_tokens(self) -> dict[str, Any]:
     """Call Lambda login endpoint and fetch tokens directly."""
     payload = {
        "username": self.username,
        "password": self.password,
        "grant_type": "password",
       }

     try:
        async with self.session.post(
            API_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:

            if resp.status == 401:
                raise ConfigEntryAuthFailed("Invalid username or password")

            text = await resp.text()

            if resp.status != 200:
                raise Exception(f"Login failed: {resp.status}, body={text}")

            # Lambda returns wrapper JSON
            raw = json.loads(text)
            data = self._extract_lambda_body(raw)

            if "access_token" not in data:
                raise Exception(f"access_token missing in login response: {data}")

            return data

     except aiohttp.ClientError as err: 
        raise Exception(f"Network error during login: {err}") from err
    
    async def _async_exchange_authcode_for_token(self, auth_code: str) -> dict[str, Any]:
        """Exchange authCode for Cognito tokens using PUBLIC client (no secret)."""
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        form = {
            "grant_type": "authorization_code",
            "client_id": self.cognito_client_id,
            "code": auth_code,
            "redirect_uri": self.cognito_redirect_uri,
        }

        try:
            async with self.session.post(
                 self.cognito_token_url,
                data=form,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:

                text = await resp.text()
                print("EOT HOME Cognito Token Exchange Response:", text)

                if resp.status in (400, 401):
                    raise ConfigEntryAuthFailed(f"Cognito token exchange failed: {text}")

                if resp.status != 200:
                    raise Exception(f"Cognito error: {resp.status}, body={text}")

                return json.loads(text)

        except aiohttp.ClientError as err:
            raise Exception(f"Network error during token exchange: {err}") from err

    async def _async_refresh_token(self) -> None:
        """Refresh access token using refresh_token via Cognito PUBLIC client."""
        if not self._refresh_token:
            raise ConfigEntryAuthFailed("No refresh token available")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        form = {
            "grant_type": "refresh_token",
            "client_id": self.cognito_client_id,
            "refresh_token": self._refresh_token,
        }

        try:
            async with self.session.post(
                self.cognito_token_url,
                data=form,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:

                text = await resp.text()

                if resp.status in (400, 401):
                    raise ConfigEntryAuthFailed(f"Refresh token invalid/expired: {text}")

                if resp.status != 200:
                    raise Exception(f"Token refresh failed: {resp.status}, body={text}")

                data = json.loads(text)

                # Refresh response often doesn't return refresh_token again
                if "refresh_token" not in data:
                    data["refresh_token"] = self._refresh_token

                self._update_tokens(data)

        except aiohttp.ClientError as err:
            raise Exception(f"Network error during refresh: {err}") from err

    def _update_tokens(self, data: dict[str, Any]) -> None:
        """Store Cognito token response."""
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)

        if not access_token:
            raise Exception(f"access_token missing in response: {data}")

        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

    def _extract_lambda_body(self, raw: dict[str, Any]) -> dict[str, Any]:

        if isinstance(raw, dict) and "body" in raw:
            body = raw.get("body", "{}")
            if isinstance(body, str):
                return json.loads(body)
            if isinstance(body, dict):
                return body
        return raw
    
