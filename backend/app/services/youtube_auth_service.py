import glob
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse

import requests
from app.config import Config

logger = logging.getLogger("app")


class YouTubeAuthService:
    _oauth_config: Optional[Dict[str, Any]] = None
    _pending_auth_states: dict[str, dict[str, Any]] = {}
    _pending_uploads: dict[str, dict[str, Any]] = {}
    _scope = "https://www.googleapis.com/auth/youtube.readonly"

    @staticmethod
    def _auth_dir(user_id: int) -> Path:
        return Path(Config.USER_DOCUMENTS_PATH) / str(user_id) / "youtube_auth"

    @classmethod
    def _discover_client_file(cls) -> Path:
        configured = os.environ.get("GOOGLE_OAUTH_CLIENT_FILE")
        if configured:
            path = Path(configured)
            if path.exists():
                return path

        matches = sorted(glob.glob("client_secret_*.json"))
        if not matches:
            raise FileNotFoundError("Google OAuth client JSON file not found")
        return Path(matches[0])

    @classmethod
    def _load_oauth_config(cls) -> Dict[str, Any]:
        if cls._oauth_config is not None:
            return cls._oauth_config

        try:
            client_file = cls._discover_client_file()
            with open(client_file, "r", encoding="utf-8") as handle:
                raw = json.load(handle)

            web_config = raw.get("web") or raw
            cls._oauth_config = {
                "client_id": web_config["client_id"],
                "client_secret": web_config["client_secret"],
                "auth_uri": web_config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": web_config.get("token_uri", "https://oauth2.googleapis.com/token"),
                "redirect_uris": web_config.get("redirect_uris", []),
            }
        except Exception as e:
            logger.info(f"[YouTubeAuth] Client secret file load failed: {e}. Trying env vars...")
            client_id = os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
            redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
            if not client_id or not client_secret:
                raise ValueError("Neither Google OAuth client JSON file nor GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET environment variables found.")
            cls._oauth_config = {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri] if redirect_uri else [],
            }

        return cls._oauth_config

    @classmethod
    def _callback_url(cls, root_url: str, url_prefix: str = "") -> str:
        base = root_url.rstrip("/")
        prefix = (url_prefix or "").rstrip("/")
        if prefix:
            return f"{base}{prefix}/admin/auth/google/callback"
        return f"{base}/admin/auth/google/callback"

    @classmethod
    def _select_redirect_uri(cls, *, root_url: str, url_prefix: str, config: Dict[str, Any]) -> str:
        preferred = cls._callback_url(root_url=root_url, url_prefix=url_prefix)
        registered = config.get("redirect_uris") or []
        if preferred in registered:
            return preferred

        preferred_parts = urlparse(preferred)
        preferred_origin = f"{preferred_parts.scheme}://{preferred_parts.netloc}"
        preferred_path = preferred_parts.path.rstrip("/")

        same_origin = [uri for uri in registered if uri.startswith(preferred_origin)]
        if same_origin:
            if preferred_path:
                prefixed_match = [
                    uri for uri in same_origin
                    if urlparse(uri).path.rstrip("/") == preferred_path
                ]
                if prefixed_match:
                    return prefixed_match[0]

            logger.warning(
                "[YouTubeAuth] Preferred redirect URI is not registered in OAuth JSON. preferred=%s registered_same_origin=%s",
                preferred,
                same_origin,
            )
            for uri in same_origin:
                if urlparse(uri).path.rstrip("/").endswith("/admin/auth/google/callback"):
                    return uri
            return same_origin[0]

        if registered:
            logger.warning(
                "[YouTubeAuth] No same-origin redirect URI registered. preferred=%s registered=%s",
                preferred,
                registered,
            )
            return registered[0]
        return preferred

    @classmethod
    def _token_file_for_upload(cls, user_id: int, pending_upload_id: str) -> str:
        auth_dir = cls._auth_dir(user_id)
        auth_dir.mkdir(parents=True, exist_ok=True)
        return str(auth_dir / f"pending_{pending_upload_id}.json")

    @classmethod
    def create_pending_upload(
        cls,
        *,
        user_id: int,
        video_url: str,
        title: Optional[str] = None,
        language: Optional[str] = "en",
    ) -> str:
        pending_upload_id = str(uuid.uuid4())
        cls._pending_uploads[pending_upload_id] = {
            "user_id": user_id,
            "video_url": video_url,
            "title": title,
            "language": language,
            "created_at": time.time(),
        }
        logger.info(
            "[YouTubeAuth] Pending upload created (user=%s, pending_upload_id=%s)",
            user_id,
            pending_upload_id,
        )
        return pending_upload_id

    @classmethod
    def start_upload_auth(
        cls,
        *,
        user_id: int,
        pending_upload_id: str,
        root_url: str,
        url_prefix: str = "",
    ) -> Dict[str, Any]:
        config = cls._load_oauth_config()
        state = str(uuid.uuid4())
        redirect_uri = cls._select_redirect_uri(root_url=root_url, url_prefix=url_prefix, config=config)

        cls._pending_auth_states[state] = {
            "user_id": user_id,
            "pending_upload_id": pending_upload_id,
            "redirect_uri": redirect_uri,
            "created_at": time.time(),
        }
        logger.info(
            "[YouTubeAuth] Starting OAuth account selection (user=%s, pending_upload_id=%s, state=%s, redirect_uri=%s, scope=%s)",
            user_id,
            pending_upload_id,
            state,
            redirect_uri,
            cls._scope,
        )

        query = urlencode(
            {
                "client_id": config["client_id"],
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": cls._scope,
                "access_type": "offline",
                "prompt": "select_account consent",
                "state": state,
                "include_granted_scopes": "true",
            }
        )
        return {
            "auth_url": f"{config['auth_uri']}?{query}",
            "state": state,
        }

    @classmethod
    def complete_upload_auth(cls, *, state: str, code: str) -> Dict[str, Any]:
        logger.info(
            "[YouTubeAuth] OAuth callback received (state_present=%s, code_present=%s)",
            bool(state),
            bool(code),
        )
        session = cls._pending_auth_states.get(state)
        if not session:
            raise ValueError("Upload auth session not found or expired")

        pending_upload_id = session["pending_upload_id"]
        pending_upload = cls._pending_uploads.get(pending_upload_id)
        if not pending_upload:
            cls._pending_auth_states.pop(state, None)
            raise ValueError("Pending upload not found or expired")

        config = cls._load_oauth_config()
        response = requests.post(
            config["token_uri"],
            data={
                "code": code,
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "redirect_uri": session["redirect_uri"],
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
        payload = response.json()
        if response.status_code != 200:
            logger.warning("[YouTubeAuth] OAuth token exchange failed: %s", payload)
            raise ValueError(payload.get("error_description") or payload.get("error") or "Google authentication failed")

        logger.info(
            "[YouTubeAuth] OAuth token exchange succeeded (user=%s, pending_upload_id=%s, token_keys=%s, access_token_present=%s, refresh_token_present=%s, expires_in=%s, token_type=%s, scope=%s)",
            pending_upload["user_id"],
            pending_upload_id,
            sorted(payload.keys()),
            bool(payload.get("access_token")),
            bool(payload.get("refresh_token")),
            payload.get("expires_in"),
            payload.get("token_type"),
            payload.get("scope"),
        )

        token_file = cls._token_file_for_upload(pending_upload["user_id"], pending_upload_id)
        token_payload = {
            "access_token": payload.get("access_token"),
            "refresh_token": payload.get("refresh_token"),
            "expires": int(time.time()) + int(payload.get("expires_in", 0)),
            "visitorData": None,
            "po_token": None,
        }
        with open(token_file, "w", encoding="utf-8") as handle:
            json.dump(token_payload, handle)

        pending_upload["oauth_token_file"] = token_file
        pending_upload["oauth_completed_at"] = time.time()
        cls._pending_auth_states.pop(state, None)

        logger.info(
            "[YouTubeAuth] Upload auth completed (user=%s, pending_upload_id=%s, token_file=%s)",
            pending_upload["user_id"],
            pending_upload_id,
            token_file,
        )
        return {
            "pending_upload_id": pending_upload_id,
            "user_id": pending_upload["user_id"],
            "oauth_token_file": token_file,
        }

    @classmethod
    def get_pending_upload(cls, pending_upload_id: str) -> Optional[Dict[str, Any]]:
        return cls._pending_uploads.get(pending_upload_id)

    @classmethod
    def pop_pending_upload(cls, pending_upload_id: str) -> Optional[Dict[str, Any]]:
        return cls._pending_uploads.pop(pending_upload_id, None)

    @classmethod
    def cleanup_upload_auth(cls, pending_upload_id: str, token_file: Optional[str] = None) -> None:
        if token_file and os.path.exists(token_file):
            try:
                os.remove(token_file)
            except OSError:
                logger.warning("[YouTubeAuth] Failed to remove temporary token file: %s", token_file, exc_info=True)
        cls._pending_uploads.pop(pending_upload_id, None)