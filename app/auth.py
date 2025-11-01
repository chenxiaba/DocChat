"""Authentication routes providing Google OAuth and WeChat QR-code login flows."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, Dict, Tuple, Literal
from urllib.parse import urlencode
from uuid import uuid4

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

try:  # pragma: no cover - optional dependency safety
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except ModuleNotFoundError as exc:  # pragma: no cover - defensive guard
    raise RuntimeError(
        "google-auth package must be installed to use Google login endpoints"
    ) from exc

from .config import Settings, get_settings


class AuthStateManager:
    """Track OAuth state parameters with expiration to prevent CSRF attacks."""

    def __init__(self, default_ttl_seconds: int = 600) -> None:
        self._default_ttl_seconds = default_ttl_seconds
        self._states: Dict[str, Tuple[str, float, int]] = {}
        self._lock = Lock()

    @property
    def default_ttl_seconds(self) -> int:
        return self._default_ttl_seconds

    def create_state(self, provider: str, ttl_seconds: int | None = None) -> str:
        ttl = ttl_seconds or self._default_ttl_seconds
        token = uuid4().hex
        now = time.time()
        with self._lock:
            self._cleanup(now)
            self._states[token] = (provider, now, ttl)
        return token

    def validate_state(self, provider: str, token: str | None) -> None:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing state parameter",
            )

        now = time.time()
        with self._lock:
            self._cleanup(now)
            stored = self._states.pop(token, None)

        if not stored or stored[0] != provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state parameter",
            )

        _, created_at, ttl = stored
        if now - created_at > ttl:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state parameter",
            )

    def _cleanup(self, now: float) -> None:
        expired = [
            token
            for token, (_, created_at, ttl) in self._states.items()
            if now - created_at > ttl
        ]
        for token in expired:
            self._states.pop(token, None)


router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger(__name__)


_state_manager: AuthStateManager | None = None


def get_state_manager(settings: Settings = Depends(get_settings)) -> AuthStateManager:
    global _state_manager
    if (
        _state_manager is None
        or _state_manager.default_ttl_seconds != settings.oauth_state_ttl_seconds
    ):
        _state_manager = AuthStateManager(settings.oauth_state_ttl_seconds)
    return _state_manager


def _parse_json_response(response: httpx.Response, provider: str) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError as exc:  # pragma: no cover - defensive guard
        display_provider = provider.replace("_", " ").title()
        logger.warning(
            "%s_invalid_json",
            provider,
            error=str(exc),
            body=response.text[:256],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{display_provider} response parsing failed",
        ) from exc


def _ensure_google_config(settings: Settings) -> None:
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google login is not configured",
        )


def _ensure_wechat_config(settings: Settings) -> None:
    if not settings.wechat_app_id or not settings.wechat_app_secret or not settings.wechat_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WeChat login is not configured",
        )


class OAuthInitResponse(BaseModel):
    status: Literal["ready"] = "ready"
    state: str = Field(..., min_length=8)
    expires_in: int = Field(..., ge=1)


class GoogleInitResponse(OAuthInitResponse):
    provider: Literal["google"] = "google"
    authorization_url: HttpUrl


class WeChatInitResponse(OAuthInitResponse):
    provider: Literal["wechat"] = "wechat"
    login_url: HttpUrl


class GoogleProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    name: str | None = None
    picture: str | None = None
    locale: str | None = None


class GoogleCredentials(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    scope: str | None = None
    token_type: str | None = None


class GoogleCallbackResponse(BaseModel):
    status: Literal["success"] = "success"
    provider: Literal["google"] = "google"
    profile: GoogleProfile
    credentials: GoogleCredentials


class WeChatProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    openid: str | None = None
    nickname: str | None = None
    headimgurl: str | None = None
    sex: int | None = None
    province: str | None = None
    city: str | None = None
    country: str | None = None


class WeChatCredentials(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    scope: str | None = None
    openid: str | None = None
    unionid: str | None = None


class WeChatCallbackResponse(BaseModel):
    status: Literal["success"] = "success"
    provider: Literal["wechat"] = "wechat"
    credentials: WeChatCredentials
    profile: WeChatProfile


@router.get("/google/login", response_model=GoogleInitResponse)
async def initiate_google_login(
    settings: Settings = Depends(get_settings),
    state_manager: AuthStateManager = Depends(get_state_manager),
) -> GoogleInitResponse:
    """Generate the Google OAuth authorization URL and state token."""

    _ensure_google_config(settings)
    state = state_manager.create_state("google", settings.oauth_state_ttl_seconds)
    params = {
        "client_id": settings.google_client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": settings.google_redirect_uri,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    authorization_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return GoogleInitResponse(
        state=state,
        expires_in=settings.oauth_state_ttl_seconds,
        authorization_url=authorization_url,
    )


@router.get("/google/callback", response_model=GoogleCallbackResponse)
async def handle_google_callback(
    code: str = Query(..., description="Authorization code returned by Google"),
    state: str | None = Query(default=None, description="State parameter for CSRF protection"),
    settings: Settings = Depends(get_settings),
    state_manager: AuthStateManager = Depends(get_state_manager),
) -> GoogleCallbackResponse:
    """Exchange authorization code for tokens and return verified Google profile data."""

    _ensure_google_config(settings)
    state_manager.validate_state("google", state)

    async with httpx.AsyncClient(timeout=settings.oauth_http_timeout_seconds) as client:
        try:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.google_redirect_uri,
                },
            )
            token_response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("google_token_timeout", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Google token endpoint timeout",
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "google_token_http_error",
                status_code=exc.response.status_code,
                response=exc.response.text,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google token exchange failed: {exc.response.text}",
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("google_token_request_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to contact Google token endpoint",
            ) from exc

    token_data = _parse_json_response(token_response, "google")
    id_token_value = token_data.get("id_token")
    if not id_token_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google response did not contain an id_token",
        )

    try:
        google_request = google_requests.Request()
        verified_token = id_token.verify_oauth2_token(id_token_value, google_request, settings.google_client_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Google ID token: {exc}") from exc

    profile = GoogleProfile(
        id=verified_token.get("sub"),
        email=verified_token.get("email"),
        email_verified=verified_token.get("email_verified"),
        name=verified_token.get("name"),
        picture=verified_token.get("picture"),
        locale=verified_token.get("locale"),
    )

    credentials = GoogleCredentials(
        access_token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in"),
        scope=token_data.get("scope"),
        token_type=token_data.get("token_type"),
    )

    return GoogleCallbackResponse(profile=profile, credentials=credentials)


@router.get("/wechat/qrcode", response_model=WeChatInitResponse)
async def initiate_wechat_login(
    settings: Settings = Depends(get_settings),
    state_manager: AuthStateManager = Depends(get_state_manager),
) -> WeChatInitResponse:
    """Return the QR code login URL for WeChat with a generated state parameter."""

    _ensure_wechat_config(settings)
    state = state_manager.create_state("wechat", settings.oauth_state_ttl_seconds)
    params = {
        "appid": settings.wechat_app_id,
        "redirect_uri": settings.wechat_redirect_uri,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": state,
    }
    login_url = (
        "https://open.weixin.qq.com/connect/qrconnect?"
        + urlencode(params)
        + "#wechat_redirect"
    )
    return WeChatInitResponse(
        state=state,
        expires_in=settings.oauth_state_ttl_seconds,
        login_url=login_url,
    )


@router.get("/wechat/callback", response_model=WeChatCallbackResponse)
async def handle_wechat_callback(
    code: str = Query(..., description="Authorization code returned by WeChat"),
    state: str | None = Query(default=None, description="State parameter for CSRF protection"),
    settings: Settings = Depends(get_settings),
    state_manager: AuthStateManager = Depends(get_state_manager),
) -> WeChatCallbackResponse:
    """Exchange the WeChat authorization code for tokens and return basic user information."""

    _ensure_wechat_config(settings)
    state_manager.validate_state("wechat", state)

    profile = WeChatProfile()
    async with httpx.AsyncClient(timeout=settings.oauth_http_timeout_seconds) as client:
        try:
            token_response = await client.get(
                "https://api.weixin.qq.com/sns/oauth2/access_token",
                params={
                    "appid": settings.wechat_app_id,
                    "secret": settings.wechat_app_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("wechat_token_timeout", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="WeChat token endpoint timeout",
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "wechat_token_http_error",
                status_code=exc.response.status_code,
                response=exc.response.text,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"WeChat token exchange failed: {exc.response.text}",
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("wechat_token_request_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to contact WeChat token endpoint",
            ) from exc

        token_data = _parse_json_response(token_response, "wechat")
        if token_data.get("errcode"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"WeChat error: {token_data.get('errmsg', 'unknown error')}",
            )

        access_token = token_data.get("access_token")
        openid = token_data.get("openid")

        if access_token and openid:
            try:
                user_info_response = await client.get(
                    "https://api.weixin.qq.com/sns/userinfo",
                    params={"access_token": access_token, "openid": openid},
                )
                if user_info_response.status_code == status.HTTP_200_OK:
                    profile = WeChatProfile(
                        **_parse_json_response(user_info_response, "wechat_profile")
                    )
            except httpx.HTTPError as exc:
                logger.warning("wechat_profile_request_failed", error=str(exc))

    credentials = WeChatCredentials(
        access_token=access_token,
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in"),
        scope=token_data.get("scope"),
        openid=openid,
        unionid=token_data.get("unionid"),
    )

    return WeChatCallbackResponse(credentials=credentials, profile=profile)

