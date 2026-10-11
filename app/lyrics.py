"""Songteksten via LRCLIB (lrclib.net)."""
import bisect
import re
import threading
import time

import requests

API = "https://lrclib.net/api"
HEADERS = {"User-Agent": "SpotiScherm/1.2 (hobbyproject)"}
RETRY_SECONDS = 60
STAMP = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


class Lyrics:
    def __init__(self, synced=None, plain=None, instrumental=False, error=False):
        self.lines = synced or []            # [(seconden, tekst), ...] als hij meeloopt
        self.times = [t for t, _ in self.lines]
        self.plain = plain                   # gewone tekst als er geen tijden zijn
        self.instrumental = instrumental
        self.error = error

    @property
    def found(self):
        return bool(self.lines or self.plain or self.instrumental)

    def index_at(self, seconds):
        """Welke regel er nu klinkt; -1 als het eerste woord nog moet komen."""
        return bisect.bisect_right(self.times, seconds) - 1


def parse_lrc(text):
    lines = []
    for raw in text.splitlines():
        words = STAMP.sub("", raw).strip()
        for minutes, seconds in STAMP.findall(raw):
            lines.append((int(minutes) * 60 + float(seconds), words or "♪"))
    return sorted(lines)


def clean_title(name):
    """'Song - Remastered 2011 (feat. X)' -> 'Song', voor als de precieze naam niks oplevert."""
    name = re.sub(r"\s+-\s+.*$", "", name)
    return re.sub(r"\s*[(\[](feat\.|ft\.|with)[^)\]]*[)\]]", "", name, flags=re.I).strip()


def to_lyrics(data):
    return Lyrics(synced=parse_lrc(data.get("syncedLyrics") or ""), plain=data.get("plainLyrics"),
                  instrumental=bool(data.get("instrumental")))


def fetch(item):
    artist = (item.get("artists") or [{}])[0].get("name", "")
    title = item.get("name", "")
    duration = (item.get("duration_ms") or 0) / 1000
    r = requests.get(f"{API}/get", headers=HEADERS, timeout=10, params={
        "artist_name": artist, "track_name": title,
        "album_name": (item.get("album") or {}).get("name", ""), "duration": round(duration)})
    if r.status_code == 200:
        return to_lyrics(r.json())
    if r.status_code != 404:
        r.raise_for_status()
    r = requests.get(f"{API}/search", headers=HEADERS, timeout=10,
                     params={"artist_name": artist, "track_name": clean_title(title)})
    r.raise_for_status()
    close = [c for c in r.json() if abs((c.get("duration") or 0) - duration) <= 4]
    close.sort(key=lambda c: not c.get("syncedLyrics"))  # meelopende eerst
    return to_lyrics(close[0]) if close else Lyrics()


class LyricsCache:
    """Haalt teksten op de achtergrond op en onthoudt ze per nummer."""

    def __init__(self):
        self.lock = threading.Lock()
        self._done = {}
        self._busy = set()

    def get(self, item):
        """Lyrics, of None als hij nog geladen wordt."""
        uri = item.get("uri")
        with self.lock:
            result = self._done.get(uri)
            if result and not (result.error and time.monotonic() - result.failed_at > RETRY_SECONDS):
                return result
            if uri in self._busy:
                return None
            self._busy.add(uri)
        threading.Thread(target=self._load, args=(item,), daemon=True).start()
        return None

    def _load(self, item):
        if item.get("type") == "episode":
            result = Lyrics()
        else:
            try:
                result = fetch(item)
            except (requests.RequestException, ValueError) as err:
                print(f"Songtekst ophalen mislukt: {err}", flush=True)
                result = Lyrics(error=True)
                result.failed_at = time.monotonic()
        with self.lock:
            if len(self._done) > 50:
                self._done.clear()
            self._done[item.get("uri")] = result
            self._busy.discard(item.get("uri"))
