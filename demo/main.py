"""SpotiScherm in je browser: de echte app, met een nep-Spotify eronder.

Gebouwd met pygbag (pygame -> WebAssembly), zie demo/README.md. In de browser zijn er geen
threads, geen netwerk en geen GPIO; daarom:
  - draaien de achtergrondklussen van de app hier gewoon in de hoofdlus;
  - vervangt FakeSpotify de Spotify Web API (playlists, albums en hoezen zijn verzonnen);
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
sys.modules.update({"spotipy": _spotipy, "spotipy.exceptions": _spotipy.exceptions,
                    "spotipy.oauth2": _spotipy.oauth2})

_web = types.ModuleType("web")
_web.SettingsServer = object
_updates = types.ModuleType("updates")
_updates.Updates = object
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


ARTISTS = {"a1": "The Example Band", "a2": "Pixel Parade", "a3": "Nachtvlinder"}
ALBUMS = {  # id -> (naam, artiest, jaar, soort, nummers (naam, seconden))
    "b1": ("Night Drive", "a1", "2024", "album", [("Neon Horizon", 228), ("City Lights", 201), ("Midnight Run", 245),
                                                  ("Chrome Hearts", 189), ("Last Exit", 260)]),
    "b2": ("Afterglow", "a1", "2021", "album", [("Sunset Boulevard", 214), ("Static Love", 198),
                                                ("Electric Dreams", 233)]),
    "b3": ("8-bit Summer", "a2", "2025", "album", [("Arcade Heart", 176), ("Level Up", 183), ("Bonus Stage", 205),
                                                   ("Game Over (Not Yet)", 221)]),
    "b4": ("Zomeravond", "a3", "2023", "single", [("Zomeravond", 199)]),
    "b5": ("Lichtjes", "a3", "2022", "album", [("Lichtjes in de stad", 236), ("Fietsen naar huis", 208),
                                               ("Tot morgen", 247)]),
}
TRACKS, ALBUM_TRACKS = {}, {}
for album_id, (album_name, artist_id, year, kind, songs) in ALBUMS.items():
    ALBUM_TRACKS[album_id] = []
    for n, (song, seconds) in enumerate(songs):
        track_id = f"{album_id}t{n}"
        ALBUM_TRACKS[album_id].append(track_id)
        TRACKS[track_id] = (song, seconds * 1000, artist_id, album_id)
PLAYLISTS = {
    "p1": ("Avondrit", ["b1t0", "b3t0", "b5t0", "b2t2", "b1t1", "b4t0", "b3t2", "b1t3"]),
    "p2": ("Synthwave Classics", ["b2t0", "b1t2", "b2t1", "b1t4", "b2t2"]),
    "p3": ("Feestje", ["b3t1", "b3t3", "b1t0", "b5t1", "b3t0"]),
    "p4": ("Rustig aan", ["b5t2", "b4t0", "b5t0", "b2t1"]),
}
LYRICS_LINES = ["Headlights painting lines across the dark", "Radio is humming something new",
                "Every city light becomes a spark", "And every spark is leading back to you", "♪",
                "Drive, drive, into the neon horizon", "Where the night is ours to keep",
                "Drive, drive, with the windows wide open", "We don't need the stars to sleep", "Oh-oh, oh-oh",
                "Into the neon horizon", "♪"]


def artist_obj(artist_id):
    return {"id": artist_id, "uri": f"spotify:artist:{artist_id}", "name": ARTISTS[artist_id], "type": "artist"}


def album_obj(album_id):
    name, artist_id, year, kind, _ = ALBUMS[album_id]
    return {"id": album_id, "uri": f"spotify:album:{album_id}", "name": name, "album_type": kind,
            "release_date": f"{year}-05-01", "artists": [artist_obj(artist_id)],
            "images": [{"url": f"demo://hoes/{album_id}.jpg", "width": 300, "height": 300}]}


def track_obj(track_id):
    name, ms, artist_id, album_id = TRACKS[track_id]
    return {"id": track_id, "uri": f"spotify:track:{track_id}", "type": "track", "name": name, "duration_ms": ms,
            "artists": [artist_obj(artist_id)], "album": album_obj(album_id)}


def playlist_obj(playlist_id):
    name, tracks = PLAYLISTS[playlist_id]
    return {"id": playlist_id, "uri": f"spotify:playlist:{playlist_id}", "name": name,
            "owner": {"display_name": "Demo"}, "tracks": {"total": len(tracks)}}


def make_covers():
    for album_id in ALBUMS:
        COVERS[f"demo://hoes/{album_id}.jpg"] = cover(album_id)


class FakeSpotify:
    """Doet alsof het de Spotify Web API is, met de verzonnen muziek hierboven."""

    def __init__(self):
        self.devices_list = [
            {"id": "d1", "name": "Woonkamer Speaker", "type": "Speaker", "volume_percent": 45},
            {"id": "d2", "name": "Keuken", "type": "Speaker", "volume_percent": 30},
            {"id": "d3", "name": "Tv Woonkamer", "type": "TV", "volume_percent": 20},
            {"id": "d4", "name": "Pixel-telefoon", "type": "Smartphone", "volume_percent": 80},
        ]
        self.device = "d1"
        self.liked = {"spotify:track:b1t0"}
        self.queue_extra = []
        self.recent = []
        self.shuffle_state, self.repeat_state = False, "off"
        self._play("spotify:playlist:p1", PLAYLISTS["p1"][1], 0, playing=True, progress=44000)

    # -- afspeelstand --

    def _play(self, context_uri, track_ids, index, playing=True, progress=0):
        self.context_uri, self.order, self.index, self.playing = context_uri, list(track_ids), index, playing
        self.progress, self.since = progress, time.monotonic()
        self.recent.insert(0, (self.order[index], time.time()))

    def _position(self):
        pos = self.progress + ((time.monotonic() - self.since) * 1000 if self.playing else 0)
        duration = TRACKS[self.order[self.index]][1]
        while pos >= duration:  # nummer afgelopen: door naar het volgende
            pos -= duration
            if not self._advance(1):
                self.playing, pos = False, 0
                break
            duration = TRACKS[self.order[self.index]][1]
        self.progress, self.since = pos, time.monotonic()
        return pos

    def _advance(self, step):
        if step > 0 and self.queue_extra:
            self.order.insert(self.index + 1, self.queue_extra.pop(0))
        if self.repeat_state == "track":
            return True
        nxt = self.index + step
        if self.shuffle_state and step > 0 and len(self.order) > 1:
            nxt = random.choice([i for i in range(len(self.order)) if i != self.index])
        if not 0 <= nxt < len(self.order):
            if self.repeat_state != "context":
                return False
            nxt %= len(self.order)
        self.index = nxt
        self.recent.insert(0, (self.order[self.index], time.time()))
        return True

    def _device(self):
        d = next(d for d in self.devices_list if d["id"] == self.device)
        return dict(d, is_active=True)

    def current_playback(self, additional_types=None):
        pos = self._position()
        return {"is_playing": self.playing, "progress_ms": int(pos), "item": track_obj(self.order[self.index]),
                "device": self._device(), "shuffle_state": self.shuffle_state, "repeat_state": self.repeat_state,
                "context": {"uri": self.context_uri, "type": self.context_uri.split(":")[1]}}

    def start_playback(self, device_id=None, context_uri=None, uris=None, offset=None):
        if context_uri:
            kind, ident = context_uri.split(":")[1:]
            ids = (PLAYLISTS[ident][1] if kind == "playlist" else ALBUM_TRACKS[ident] if kind == "album"
                   else [t for a, (_, artist, *_r) in ALBUMS.items() if artist == ident for t in ALBUM_TRACKS[a]])
            index = 0
            if offset and "position" in offset:
                index = offset["position"]
            elif offset and "uri" in offset:
                index = ids.index(offset["uri"].split(":")[-1])
            self._play(context_uri, ids, index)
        elif uris:  # een los nummer: speel het in de context van zijn album
            track_id = uris[0].split(":")[-1]
            album_id = TRACKS[track_id][3]
            self._play(f"spotify:album:{album_id}", ALBUM_TRACKS[album_id], ALBUM_TRACKS[album_id].index(track_id))
        else:
            self._position()
            self.playing, self.since = True, time.monotonic()

    def pause_playback(self, device_id=None):
        self._position()
        self.playing = False

    def next_track(self, device_id=None):
        self._position()
        if self._advance(1):
            self.progress = 0

    def previous_track(self, device_id=None):
        self._position()
        if self._advance(-1):
            self.progress = 0

    def seek_track(self, ms, device_id=None):
        self.progress, self.since = ms, time.monotonic()

    def volume(self, volume, device_id=None):
        next(d for d in self.devices_list if d["id"] == self.device)["volume_percent"] = volume

    def shuffle(self, state, device_id=None):
        self.shuffle_state = state

    def repeat(self, state, device_id=None):
        self.repeat_state = state

    def devices(self):
        return {"devices": [dict(d, is_active=d["id"] == self.device) for d in self.devices_list]}

    def transfer_playback(self, device_id, force_play=True):
        self._position()
        self.device = device_id

    # -- bibliotheek --

    def current_user_saved_tracks_contains(self, uris):
        return [u in self.liked for u in uris]

    def current_user_saved_tracks_add(self, uris):
        self.liked.update(uris)

    def current_user_saved_tracks_delete(self, uris):
        self.liked.difference_update(uris)

    def current_user_playlists(self, limit=50):
        return {"items": [playlist_obj(p) for p in PLAYLISTS], "next": None}

    def playlist_items(self, playlist_id, limit=100, additional_types=None):
        ids = PLAYLISTS[playlist_id.split(":")[-1]][1]
        return {"items": [{"track": track_obj(t)} for t in ids], "offset": 0, "next": None}

    def playlist(self, uri, fields=None):
        return playlist_obj(uri.split(":")[-1])

    def album(self, album_id):
        album = album_obj(album_id.split(":")[-1])
        album["tracks"] = {"items": [track_obj(t) for t in ALBUM_TRACKS[album["id"]]], "next": None}
        return album

    def artist(self, artist_id):
        return artist_obj(artist_id.split(":")[-1])

    def artist_albums(self, artist_id, album_type=None, limit=10):
        return {"items": [album_obj(a) for a, v in ALBUMS.items() if v[1] == artist_id], "next": None}

    def next(self, page):
        return None

    def search(self, q, limit=10, type="track"):
        q = q.lower().replace('artist:"', "").replace('"', "").strip()
        match = lambda name: not q or q in name.lower()
        tracks = [track_obj(t) for t, v in TRACKS.items() if match(v[0]) or match(ARTISTS[v[2]])]
        out = {"tracks": {"items": (tracks or [track_obj(t) for t in TRACKS])[:limit]}}
        if "artist" in type:
            out["artists"] = {"items": [artist_obj(a) for a, n in ARTISTS.items() if match(n)]}
            out["albums"] = {"items": [album_obj(a) for a, v in ALBUMS.items() if match(v[0]) or match(ARTISTS[v[1]])]}
            out["playlists"] = {"items": [playlist_obj(p) for p, v in PLAYLISTS.items() if match(v[0])]}
        return out

    def queue(self):
        upcoming = self.queue_extra + self.order[self.index + 1:]
        return {"queue": [track_obj(t) for t in upcoming[:20]]}

    def add_to_queue(self, uri, device_id=None):
        self.queue_extra.append(uri.split(":")[-1])

    def current_user_recently_played(self, limit=50):
        stamp = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(t))
        items = [{"track": track_obj(t), "played_at": stamp(when),
                  "context": {"uri": "spotify:playlist:p1"}} for t, when in self.recent[:limit]]
        older = [("b3t1", 3), ("b2t0", 26), ("b5t2", 50)]
        items += [{"track": track_obj(t), "played_at": stamp(time.time() - h * 3600),
                   "context": {"uri": "spotify:album:" + t[:2]}} for t, h in older]
        return {"items": items}


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


def fake_lyrics(item):
    """Bij elk nummer dezelfde verzonnen tekst, verdeeld over de lengte van het nummer."""
    seconds = (item.get("duration_ms") or 200000) / 1000
    step = (seconds - 20) / len(LYRICS_LINES)
    return Lyrics(synced=[(12 + i * step, line) for i, line in enumerate(LYRICS_LINES)])


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
    app.make_client = lambda scope=None: FakeSpotify()
    app.granted_scopes = lambda: set(app.SCOPES.split())
    app.local_ip = lambda: None  # geen netwerk in de browser: geen telefoonpagina
    settings = {"weer_plaats": "Utrecht", "idle_min": 2, "nacht_stijl": "uit", "nacht_van": "23:00",
                "nacht_tot": "07:00", "rust_scherm": "hoes", "taal": "nl", "lettertype": "standaard",
                "kleur": "hoes", "draaien": 0}
    lang = browser_language()
    if lang in ("nl", "en", "de", "fr", "es"):
        settings["taal"] = lang
    ui = app.Screen(SURFACE, settings, Weather(), False)
    ui.lyrics.get = fake_lyrics
    ui.p = player = app.Player()
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
        busy = False
        while not player._jobs.empty():
            fn, args = player._jobs.get_nowait()
            try:
                fn(*args)
            except Exception as err:  # zoals in Player._job_loop
                print("Demo:", err)
            busy = True
        if busy or time.monotonic() - polled > 1:
            polled = time.monotonic()
            refresh(player)
            player._sleep_tick()
        player.flush_volume()
        ui.draw()
        clock.tick(30)
        await asyncio.sleep(0)


asyncio.run(main())
