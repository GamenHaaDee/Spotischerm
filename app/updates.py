"""Nieuwe versies van GitHub: af en toe kijken of er een is, en bijwerken met één tik.

Bijwerken downloadt de zip van de nieuwste release en zet de bestanden over de oude heen.
Je eigen bestanden (config.env, .spotify-cache, instellingen.json) zitten niet in die zip
en blijven dus staan. Werkt ook als de app met scp is geïnstalleerd, zonder git.
"""
import hashlib
import io
import shutil
import tempfile
import threading
import time
import zipfile
from pathlib import Path

import requests

REPO = "GamenHaaDee/Spotischerm"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
CHECK_HOURS = 6
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "SpotiScherm"}
APP_DIR = Path(__file__).resolve().parent.parent   # ~/spotify-scherm


def version_tuple(text):
    """'v1.10' -> (1, 10); onbekend -> ()."""
    try:
        return tuple(int(part) for part in str(text).lstrip("vV").split("."))
    except ValueError:
        return ()


def _digest(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


class Updates:
    """Houdt bij wat de nieuwste release is. Kijkt elke CHECK_HOURS uur, of als je erom vraagt."""

    def __init__(self, current):
        self.current = current
        self.latest = None        # {"version", "name", "zip"}
        self.error = False
        self.checked_at = None
        self.announced = None
        self._wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    @property
    def available(self):
        return bool(self.latest and version_tuple(self.latest["version"]) > version_tuple(self.current))

    def check_now(self):
        self._wake.set()

    def announce(self):
        """True één keer per nieuwe versie, voor een melding op het scherm."""
        if self.available and self.announced != self.latest["version"]:
            self.announced = self.latest["version"]
            return True
        return False

    def _loop(self):
        time.sleep(30)  # niet meteen bij het opstarten, dan is het netwerk soms nog niet klaar
        while True:
            try:
                data = requests.get(API, headers=HEADERS, timeout=15).json()
                self.latest = {"version": data["tag_name"].lstrip("vV"), "name": data.get("name") or data["tag_name"],
                               "zip": data["zipball_url"]}
                self.error = False
            except (requests.RequestException, ValueError, KeyError) as err:
                print(f"Controleren op updates mislukt: {err}", flush=True)
                self.error = True
            self.checked_at = time.time()
            self._wake.wait(CHECK_HOURS * 3600)
            self._wake.clear()

    def install(self):
        """Download en zet de nieuwe versie neer. Geeft (gelukt, install.sh veranderd?) terug."""
        before = _digest(APP_DIR / "install.sh")
        data = requests.get(self.latest["zip"], headers=HEADERS, timeout=60).content
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(tmp)
            # GitHub zet alles in één map, bijv. GamenHaaDee-Spotischerm-2bb5e7b/
            root = next(p for p in Path(tmp).iterdir() if p.is_dir())
            if not (root / "app" / "spotischerm.py").exists():
                raise ValueError("onverwachte inhoud van de zip")
            for src in root.rglob("*"):
                if src.is_file():
                    dest = APP_DIR / src.relative_to(root)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
        return True, _digest(APP_DIR / "install.sh") != before
