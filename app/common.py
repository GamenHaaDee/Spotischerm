"""Gedeelde instellingen en de Spotify-client voor SpotiScherm."""
import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import spotipy
from spotipy.exceptions import SpotifyException
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
    "user-top-read",
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


# Tot wanneer (time.time) Spotify ons laat wachten na "te veel verzoeken" (429). Staat ook in een
# bestandje, zodat een herstart (of auth.py) niet meteen weer een verzoek stuurt.
WAIT_PATH = ROOT / ".spotify-wachten"
try:
    _blocked_until = float(WAIT_PATH.read_text())
except (OSError, ValueError):
    _blocked_until = 0.0


def wait_left():
    """Hoeveel seconden Spotify ons nog laat wachten (0 = niet)."""
    return max(0.0, _blocked_until - time.time())


def _block(seconds):
    global _blocked_until
    _blocked_until = time.time() + seconds
    try:
        WAIT_PATH.write_text(f"{_blocked_until:.0f}")
    except OSError:
        pass


COUNT_PATH = ROOT / ".spotify-teller"
COUNT_SAVE = 60  # zo vaak (s) de telling bewaren; niet bij elk verzoek, dat slijt de SD-kaart


class RequestCounter:
    """Telt de verzoeken die echt naar Spotify gaan: dit uur, vandaag en gisteren.

    Spotify zegt niet hoeveel er mogen; zo zie je op de Info-pagina hoeveel de app er doet.
    """

    def __init__(self, path):
        self.path, self.lock, self.saved = path, threading.Lock(), float("-inf")  # nog nooit bewaard
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        self.day, self.today = data.get("dag", ""), int(data.get("vandaag", 0))
        self.yesterday = int(data.get("gisteren", 0))
        self.hour, self.this_hour = data.get("uur", ""), int(data.get("dit_uur", 0))

    def _roll(self, now):
        """Een nieuwe dag of een nieuw uur: opnieuw beginnen met tellen."""
        day, hour = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%dT%H")
        if day != self.day:
            # Was de vorige telling van gisteren, dan is dat "gisteren"; anders weten we het niet.
            self.yesterday = self.today if self.day == (now - timedelta(days=1)).strftime("%Y-%m-%d") else 0
            self.day, self.today = day, 0
        if hour != self.hour:
            self.hour, self.this_hour = hour, 0

    def add(self, now=None):
        with self.lock:
            self._roll(now or datetime.now())
            self.today += 1
            self.this_hour += 1
            if time.monotonic() - self.saved > COUNT_SAVE:
                self._save()

    def counts(self, now=None):
        """(dit uur, vandaag, gisteren)"""
        with self.lock:
            self._roll(now or datetime.now())
            return self.this_hour, self.today, self.yesterday

    def _save(self):
        self.saved = time.monotonic()
        data = {"dag": self.day, "vandaag": self.today, "gisteren": self.yesterday,
                "uur": self.hour, "dit_uur": self.this_hour}
        try:
            self.path.write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass


counter = RequestCounter(COUNT_PATH)


class Client(spotipy.Spotify):
    """Spotify-client die bij "te veel verzoeken" niet blijft hangen.

    spotipy wacht zelf zo lang als Spotify vraagt, en dat kan uren zijn: dan staat de hele app
    stil. Deze client onthoudt het, geeft meteen een fout (429), en stuurt tot die tijd niets.
    """

    def _build_session(self):
        super()._build_session()
        # urllib3 wacht bij een 429 met Retry-After anders tóch, ook als 429 niet in status_forcelist staat.
        for adapter in self._session.adapters.values():
            adapter.max_retries = adapter.max_retries.new(respect_retry_after_header=False)

    def _internal_call(self, method, url, payload, params):
        left = wait_left()
        if left > 0:
            raise SpotifyException(429, -1, "Spotify laat ons nog even wachten",
                                   headers={"Retry-After": str(int(left) + 1)})
        counter.add()
        try:
            return super()._internal_call(method, url, payload, params)
        except SpotifyException as err:
            if err.http_status == 429:
                try:
                    seconds = int((err.headers or {}).get("Retry-After"))
                except (TypeError, ValueError):
                    seconds = 30
                _block(max(seconds, 1))
                print(f"Spotify: te veel verzoeken, {seconds} s wachten", flush=True)
            raise


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
    # 429 niet in de lijst: dat handelt Client zelf af, zonder te blijven wachten.
    return Client(auth_manager=auth, requests_timeout=8, retries=2, status_forcelist=(500, 502, 503, 504))
