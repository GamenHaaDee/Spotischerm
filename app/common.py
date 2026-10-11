"""Gedeelde instellingen en de Spotify-client voor SpotiScherm."""
import json
import os
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.env"
CACHE_PATH = ROOT / ".spotify-cache"
SETTINGS_PATH = ROOT / "instellingen.json"   # wat je op het scherm instelt; wint van config.env

SCOPES = " ".join([
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-read-recently-played",
    "user-library-read",
    "user-library-modify",
])


def load_config():
    """Leest config.env in als omgevingsvariabelen (bestaande waarden winnen)."""
    if CONFIG_PATH.exists():
        for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

    missing = [k for k in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Vul dit in config.env in: {', '.join(missing)}")


def load_settings():
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    # Eerst naar een tijdelijk bestand, zodat stroom eraf halen het bestand niet half achterlaat.
    tmp = SETTINGS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(SETTINGS_PATH)


def granted_scopes():
    """Welke toestemmingen het opgeslagen Spotify-token heeft (leeg als er nog geen is)."""
    try:
        return set(json.loads(CACHE_PATH.read_text(encoding="utf-8")).get("scope", "").split())
    except (OSError, ValueError):
        return set()


def make_client(scope=SCOPES):
    load_config()
    auth = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        scope=scope,
        cache_path=str(CACHE_PATH),
        open_browser=False,
    )
    return spotipy.Spotify(auth_manager=auth, requests_timeout=8, retries=2)
