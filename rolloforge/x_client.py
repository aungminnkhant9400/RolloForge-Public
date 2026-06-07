from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests

from config.settings import Settings
from rolloforge.models import Bookmark
from rolloforge.utils import stable_bookmark_id, utc_now_iso


LOGGER = logging.getLogger(__name__)


class XBookmarkClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.settings.x_user_agent,
                "Accept": "application/json",
            }
        )

    def has_real_auth(self) -> bool:
        return bool(self.settings.x_user_access_token)

    def auth_summary(self) -> dict[str, bool]:
        return {
            "x_user_access_token": bool(self.settings.x_user_access_token),
            "x_user_id": bool(self.settings.x_user_id),
            "x_bookmarks_source_file": bool(self.settings.x_bookmarks_source_file),
        }

    def fetch_bookmarks(self, source_file: str | None = None) -> tuple[list[Bookmark], str]:
        source_file = source_file or self.settings.x_bookmarks_source_file

        if source_file:
            LOGGER.info("Bookmark sync mode: local sample input from %s", source_file)
            return self._load_from_file(Path(source_file)), "local_file"
        if self.has_real_auth():
            LOGGER.info("Bookmark sync mode: real X API for authenticated user.")
            return self._load_from_authenticated_user(), "real_api"

        LOGGER.info("No real X auth or local source configured. Skipping sync.")
        return [], "none"

    def _load_from_file(self, path: Path) -> list[Bookmark]:
        if not path.exists():
            raise FileNotFoundError(f"Bookmark source file not found: {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        return self._normalize_collection(raw)

    def _headers(self) -> dict[str, str]:
        if not self.settings.x_user_access_token:
            raise ValueError("X_USER_ACCESS_TOKEN is required for real X bookmark sync.")
        return {"Authorization": f"Bearer {self.settings.x_user_access_token}"}

    def _ensure_success(self, response: requests.Response, context: str) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            message = (
                f"{context} failed with HTTP {response.status_code}. "
                "Confirm X_USER_ACCESS_TOKEN is a user access token with bookmark.read, tweet.read, and users.read scopes."
            )
            raise RuntimeError(message) from exc

    def _get_authenticated_user_id(self) -> str:
        if self.settings.x_user_id:
            return self.settings.x_user_id

        response = self.session.get(
            f"{self.settings.x_api_base_url}/users/me",
            headers=self._headers(),
            params={"user.fields": "id,username"},
            timeout=45,
        )
        self._ensure_success(response, "Fetching authenticated X user")
        payload = response.json()
        user_id = str(payload.get("data", {}).get("id", "")).strip()
        if not user_id:
            raise ValueError("X /2/users/me response did not contain a user ID.")
        return user_id

    def _load_from_authenticated_user(self) -> list[Bookmark]:
        user_id = self._get_authenticated_user_id()
        base_params = {
            "max_results": self.settings.x_max_results,
            "tweet.fields": "attachments,author_id,created_at,entities,lang,public_metrics,text",
            "expansions": "author_id",
            "user.fields": "id,name,username",
        }

        all_items: list[dict[str, Any]] = []
        pagination_token: str | None = None
        page_count = 0

        while page_count < self.settings.x_max_pages:
            params = dict(base_params)
            if pagination_token:
                params["pagination_token"] = pagination_token

            response = self.session.get(
                f"{self.settings.x_api_base_url}/users/{user_id}/bookmarks",
                headers=self._headers(),
                params=params,
                timeout=45,
            )
            self._ensure_success(response, "Fetching X bookmarks")
            payload = response.json()

            includes = payload.get("includes", {})
            users_by_id = {
                str(user.get("id")): user
                for user in includes.get("users", [])
                if isinstance(user, dict) and user.get("id")
            }

            for item in payload.get("data", []):
                if not isinstance(item, dict):
                    continue
                enriched = dict(item)
                author_id = str(item.get("author_id", "")).strip()
                if author_id and author_id in users_by_id:
                    enriched["user"] = users_by_id[author_id]
                all_items.append(enriched)

            page_count += 1
            pagination_token = payload.get("meta", {}).get("next_token")
            if not pagination_token:
                break

        LOGGER.info("Fetched %s bookmark record(s) across %s page(s) from X API.", len(all_items), page_count)
        return self._normalize_collection(all_items)

    def _normalize_collection(self, payload: Any) -> list[Bookmark]:
        if isinstance(payload, dict):
            if isinstance(payload.get("bookmarks"), list):
                items = payload["bookmarks"]
            elif isinstance(payload.get("data"), list):
                items = payload["data"]
            else:
                items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        normalized: list[Bookmark] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            bookmark = self._normalize_item(item)
            if bookmark:
                normalized.append(bookmark)
        return normalized

    def _normalize_item(self, item: dict[str, Any]) -> Bookmark | None:
        text = str(item.get("text") or item.get("content") or item.get("tweet_text") or "").strip()
        bookmark_id = str(item.get("id") or item.get("tweet_id") or "").strip()

        entities = item.get("entities", {}) if isinstance(item.get("entities"), dict) else {}
        urls = entities.get("urls", []) if isinstance(entities.get("urls"), list) else []
        hashtags = entities.get("hashtags", []) if isinstance(entities.get("hashtags"), list) else []

        url = str(
            item.get("url")
            or item.get("expanded_url")
            or item.get("tweet_url")
            or item.get("link")
            or ""
        ).strip()
        if not url and urls:
            first_url = urls[0]
            if isinstance(first_url, dict):
                url = str(first_url.get("expanded_url") or first_url.get("url") or "").strip()
        if not url and bookmark_id:
            url = f"https://x.com/i/web/status/{bookmark_id}"
        if not url:
            generated_id = stable_bookmark_id("missing-url", text)
            url = f"https://x.com/i/web/status/{generated_id}"

        author = (
            item.get("author")
            or item.get("screen_name")
            or item.get("username")
            or item.get("user", {}).get("screen_name")
            or item.get("user", {}).get("username")
            or item.get("user", {}).get("name")
        )
        if not bookmark_id:
            bookmark_id = stable_bookmark_id(url, text)

        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        if not tags and hashtags:
            tags = [tag.get("tag") for tag in hashtags if isinstance(tag, dict) and tag.get("tag")]

        return Bookmark(
            id=bookmark_id,
            source="x",
            url=url,
            text=text or url,
            author=str(author).strip() if author else None,
            created_at=item.get("created_at") or item.get("tweet_created_at") or utc_now_iso(),
            bookmarked_at=item.get("bookmarked_at") or item.get("saved_at") or utc_now_iso(),
            tags=[str(tag).strip() for tag in tags if str(tag).strip()],
            raw_payload=item,
        )
