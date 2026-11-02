"""SpotiScherm in je browser: de echte app, met een nep-Spotify eronder.

Gebouwd met pygbag (pygame -> WebAssembly), zie demo/README.md. In de browser zijn er geen
threads, geen netwerk en geen GPIO; daarom:
  - draaien de achtergrondklussen van de app hier gewoon in de hoofdlus;
  - vervangt FakeSpotify (app/nepspotify.py) de Spotify Web API; de hoezen tekent de demo zelf;
  - zijn requests, spotipy, de webpagina en updates vervangen door lege stand-ins.
Er gaat dus niets naar Spotify of naar een andere website.
"""
import asyncio
import os
import random
import sys
import threading
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ---------- stand-ins voor wat in de browser niet bestaat ----------

threading.Thread.start = lambda self: None  # geen threads: de demo doet alles zelf in de hoofdlus

COVERS = {}  # url -> hoes (pygame-plaatje), gevuld door make_covers()
COVER_PREFIX = "demo://hoes/"


def _get(url, **kwargs):
    raise _requests.exceptions.RequestException("geen netwerk in de demo")


_requests = types.ModuleType("requests")
_requests.exceptions = types.SimpleNamespace(RequestException=type("RequestException", (Exception,), {}))
_requests.RequestException = _requests.exceptions.RequestException
_requests.get = _get
sys.modules["requests"] = _requests


class SpotifyException(Exception):
    def __init__(self, http_status, code=-1, msg="", reason=None, headers=None):
        super().__init__(msg)
        self.http_status, self.code, self.msg, self.reason, self.headers = http_status, code, msg, reason, headers


_spotipy = types.ModuleType("spotipy")
_spotipy.Spotify = object
_spotipy.exceptions = types.ModuleType("spotipy.exceptions")
_spotipy.exceptions.SpotifyException = SpotifyException
_spotipy.oauth2 = types.ModuleType("spotipy.oauth2")
_spotipy.oauth2.SpotifyOAuth = object
_spotipy.oauth2.SpotifyOauthError = type("SpotifyOauthError", (Exception,), {})
sys.modules.update({"spotipy": _spotipy, "spotipy.exceptions": _spotipy.exceptions,
                    "spotipy.oauth2": _spotipy.oauth2})

_web = types.ModuleType("web")
_web.SettingsServer = object
_updates = types.ModuleType("updates")
_updates.Updates = object
_updates.previous = lambda: None  # geen vorige versie in de browser
_updates.restore = lambda: None
sys.modules.update({"web": _web, "updates": _updates})

import pygame  # noqa: E402

pygame.init()
SURFACE = pygame.display.set_mode((800, 480))
pygame.display.set_caption("SpotiScherm demo")

import fonts  # noqa: E402

fonts.FONT_DIRS = (HERE,)  # DejaVu staat naast dit bestand
fonts._index = None

import spotischerm as app  # noqa: E402
import discovery  # noqa: E402
import lyrics  # noqa: E402
import weather  # noqa: E402
from lyrics import Lyrics  # noqa: E402
from nepspotify import ALBUMS, FakeSpotify, lyrics_for  # noqa: E402

# pygbag heeft zelf een 'requests'; die gaat echt het internet op. Hier overal de stand-in gebruiken.
for _module in (app, discovery, lyrics, weather):
    _module.requests = _requests


# ---------- verzonnen muziek ----------

HUES = {"b1": 0.0, "b2": 0.9, "b3": 0.15, "b4": 0.6, "b5": 0.33}  # kleur per album; b1 zoals de schermafdrukken


def cover(seed):
    """Synthwave-hoes in een eigen kleur per album: lucht, gestreepte zon, bergen en een raster."""
    rnd = random.Random(seed)
    size = 300
    hue = HUES.get(seed, rnd.random())
    s = pygame.Surface((size, size))
    horizon = int(size * 0.62)

    def hsv(h, sat, val):
        c = pygame.Color(0)
        c.hsva = ((h % 1) * 360, sat, val, 100)
        return c

    for y in range(horizon):
        f = y / horizon
        s.fill(hsv(hue + 0.55 + 0.2 * f, 70, 25 + 50 * f), (0, y, size, 1))
    cx, cy, r = size // 2, int(size * 0.36), int(size * 0.25)
    pygame.draw.circle(s, hsv(hue + 0.08, 75, 100), (cx, cy), r)
    for k in range(6):
        y = cy + int(r * 0.08) + k * int(r * 0.16)
        s.fill(s.get_at((0, min(y, horizon - 1))), (cx - r - 2, y, 2 * r + 4, 2 + k * 2))
    peaks = [(0, horizon), (0, int(size * (0.5 + 0.08 * rnd.random())))]
    for i in range(1, 6):
        peaks.append((int(size * i / 6), int(size * (0.47 + 0.12 * rnd.random()))))
    peaks += [(size, int(size * 0.53)), (size, horizon)]
    pygame.draw.polygon(s, hsv(hue + 0.7, 60, 18), peaks)
    s.fill(hsv(hue + 0.7, 70, 12), (0, horizon, size, size - horizon))
    line = hsv(hue + 0.9, 70, 100)
    for k in range(1, 10):
        y = horizon + int((size - horizon) * (k / 9) ** 1.8)
        pygame.draw.line(s, line, (0, y), (size, y), 1)
    for k in range(-12, 13):
        pygame.draw.line(s, line, (cx + k * size * 0.02, horizon), (cx + k * size * 0.16, size), 1)
    return s


def make_covers():
    for album_id in ALBUMS:
        COVERS[f"{COVER_PREFIX}{album_id}.jpg"] = cover(album_id)


class Weather:
    error = None
    summary = "18° · Half bewolkt · max 22° min 14°"
    rain = "Droog de komende uren"

    def set_place(self, place):
        pass


def refresh(player):
    """Zoals Player._refresh, maar de hoes komt uit COVERS: plaatjes uit het geheugen inlezen
    (pygame.image.load met BytesIO) kan pygbag niet."""
    pb = player.sp.current_playback()
    player.last_ok = time.monotonic()
    if pb.get("is_playing"):
        player.last_playing = player.last_ok
    if time.monotonic() < player._hold_until:
        return
    with player.lock:
        player.playback, player.fetched_at = pb, time.monotonic()
        url = app.pick_image(pb)
        if url != player.art_url:
            player.art_url, player.art_image = url, COVERS.get(url)


# ---------- de hoofdlus ----------

def browser_language():
    """De taal uit het adres (demo/?lang=nl, zo opent de demopagina hem), anders die van de browser."""
    try:
        import platform
        for part in str(platform.window.location.search).lstrip("?").split("&"):
            if part.startswith("lang="):
                return part[5:].lower()
        return str(platform.window.navigator.language)[:2].lower()
    except Exception:  # buiten de browser
        return (os.environ.get("LANG") or "").lower()[:2]


async def main():
    make_covers()
    app.save_settings = lambda settings: None
    app.local_ip = lambda: None  # geen netwerk in de browser: geen telefoonpagina
    settings = {"weer_plaats": "Utrecht", "idle_min": 2, "nacht_stijl": "uit", "nacht_van": "23:00",
                "nacht_tot": "07:00", "rust_scherm": "hoes", "taal": "nl", "lettertype": "standaard",
                "kleur": "hoes", "draaien": 0}
    lang = browser_language()
    if lang in ("nl", "en", "de", "fr", "es"):
        settings["taal"] = lang
    ui = app.Screen(SURFACE, settings, Weather(), False)
    ui.lyrics.get = lambda item: Lyrics(synced=lyrics_for(item))
    ui.p = player = app.Player(sp=FakeSpotify(image_prefix=COVER_PREFIX), threads=False)
    clock = pygame.time.Clock()
    finger, polled = None, 0.0
    while True:
        for ev in pygame.event.get():
            if ui.view == "keyboard" and ev.type in (pygame.TEXTINPUT, pygame.KEYDOWN):
                ui.last_touch = time.monotonic()
                if ev.type == pygame.TEXTINPUT:
                    ui.kb_type(ev.text)
                elif ev.key == pygame.K_BACKSPACE:
                    ui.kb_backspace()
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    ui.kb_done()
                elif ev.key == pygame.K_ESCAPE:
                    ui.kb_cancel()
                continue
            if ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                if finger not in (None, ev.finger_id):
                    continue
                pos = (int(ev.x * 799), int(ev.y * 479))
                if ev.type == pygame.FINGERDOWN:
                    finger = ev.finger_id
                    ui.on_down(pos)
                elif ev.type == pygame.FINGERMOTION:
                    ui.on_move(pos)
                else:
                    finger = None
                    ui.on_up(pos)
            elif getattr(ev, "touch", False):
                continue
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                ui.on_down(ev.pos)
            elif ev.type == pygame.MOUSEMOTION and ev.buttons[0]:
                ui.on_move(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                ui.on_up(ev.pos)
            elif ev.type == pygame.MOUSEWHEEL:
                ui.scroll = max(0, ui.scroll - ev.y * ui.px(60))
        # Wat de app normaal in achtergrondthreads doet: klussen uitvoeren en de stand ophalen.
        busy = player.work()
        if busy or time.monotonic() - polled > 1:
            polled = time.monotonic()
            refresh(player)
            player._sleep_tick()
        player.flush_volume()
        ui.draw()
        clock.tick(30)
        await asyncio.sleep(0)


asyncio.run(main())
