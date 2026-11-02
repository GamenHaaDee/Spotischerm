"""Nieuwe versies van GitHub: af en toe kijken of er een is, en bijwerken met één tik.

Bijwerken downloadt de zip van de nieuwste release en zet de bestanden over de oude heen.
Je eigen bestanden (config.env, .spotify-cache, instellingen.json) zitten niet in die zip
en blijven dus staan. Werkt ook als de app met scp is geïnstalleerd, zonder git.

Vóór het bijwerken bewaren we wat er verandert in .vorige-versie/: de oude bestanden en welke
bestanden er nieuw bijkomen. Zo kun je met één tik terug naar de vorige versie (restore), en gaat
de app vanzelf terug als het bijwerken halverwege misgaat. Alleen de laatste vorige versie blijft bewaard.
"""
import hashlib
import io
import json
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
BACKUP_DIR = APP_DIR / ".vorige-versie"


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


def apply(root, app_dir, backup, version):
    """Zet de bestanden uit root over app_dir heen. Bewaart eerst in backup wat er verandert, zodat
    restore() alles terug kan zetten. Gaat het kopiëren mis, dan zet hij meteen alles terug."""
    shutil.rmtree(backup, ignore_errors=True)
    (backup / "bestanden").mkdir(parents=True)
    new_files, todo = [], []
    for src in sorted(root.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(root)
        dest = app_dir / rel
        if dest.exists():
            if dest.read_bytes() == src.read_bytes():
                continue  # niets veranderd: niets te bewaren
            keep = backup / "bestanden" / rel
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, keep)
        else:
            new_files.append(rel.as_posix())
        todo.append((src, dest))
    # Eerst opschrijven wat er gebeurt; pas daarna de bestanden vervangen.
    (backup / "info.json").write_text(json.dumps({"versie": version, "nieuw": new_files, "op": time.time()}),
                                      encoding="utf-8")
    try:
        for src, dest in todo:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    except Exception:
        restore(app_dir, backup)
        raise


def previous(backup=BACKUP_DIR):
    """{"versie", "nieuw", "op"} van de bewaarde vorige versie, of None."""
    try:
        return json.loads((backup / "info.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def restore(app_dir=APP_DIR, backup=BACKUP_DIR):
    """Zet de bewaarde vorige versie terug en ruimt de bewaarde kopie op. Geeft het versienummer."""
    info = previous(backup)
    if not info:
        raise ValueError("geen vorige versie bewaard")
    for rel in info["nieuw"]:  # wat de update toevoegde, weer weg
        (app_dir / rel).unlink(missing_ok=True)
    kept = backup / "bestanden"
    for src in kept.rglob("*"):
        if src.is_file():
            dest = app_dir / src.relative_to(kept)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    shutil.rmtree(backup, ignore_errors=True)
    return info["versie"]


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
        before = _digest(APP_DIR / "install.sh"), _digest(APP_DIR / "spotischerm.service")
        data = requests.get(self.latest["zip"], headers=HEADERS, timeout=60).content
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(tmp)
            # GitHub zet alles in één map, bijv. GamenHaaDee-Spotischerm-2bb5e7b/
            root = next(p for p in Path(tmp).iterdir() if p.is_dir())
            if not (root / "app" / "spotischerm.py").exists():
                raise ValueError("onverwachte inhoud van de zip")
            apply(root, APP_DIR, BACKUP_DIR, self.current)
        # Veranderd install.sh of spotischerm.service: dan moet install.sh nog een keer (met sudo).
        return True, (_digest(APP_DIR / "install.sh"), _digest(APP_DIR / "spotischerm.service")) != before
