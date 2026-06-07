"""X authentication manager - handles login and cookie persistence (simplified)."""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)

COOKIES_PATH = Path("/home/ubuntu/RolloForge/.x_cookies.json")
CREDENTIALS_PATH = Path("/home/ubuntu/RolloForge/.x_credentials.json")


def save_credentials(username: str, password: str) -> None:
    """Save X credentials for later use (cookies preferred, but fallback to credentials)."""
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(json.dumps({
        "username": username,
        "password": password
    }))
    LOGGER.info("Credentials saved (temporary until cookies work)")


def get_credentials() -> Optional[tuple[str, str]]:
    """Get saved credentials if available."""
    if not CREDENTIALS_PATH.exists():
        return None
    try:
        data = json.loads(CREDENTIALS_PATH.read_text())
        return (data.get("username"), data.get("password"))
    except:
        return None


def load_cookies() -> Optional[list]:
    """Load saved X cookies if they exist."""
    if not COOKIES_PATH.exists():
        LOGGER.info("No saved cookies found")
        return None
    
    try:
        cookies = json.loads(COOKIES_PATH.read_text())
        LOGGER.info(f"✅ Loaded {len(cookies)} cookies")
        return cookies
    except Exception as e:
        LOGGER.error(f"Failed to load cookies: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        save_credentials(sys.argv[1], sys.argv[2])
        print(f"✅ Credentials saved for {sys.argv[1]}")
        print("Note: Manual cookie extraction still needed until X login automation is fixed.")
    else:
        print("Usage: python x_auth.py <username> <password>")
        # Show current status
        creds = get_credentials()
        cookies = load_cookies()
        print(f"\nStatus:")
        print(f"  Credentials: {'✅ Saved' if creds else '❌ Not saved'}")
        print(f"  Cookies: {'✅ Available' if cookies else '❌ Not available'}")
