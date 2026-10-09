import io
import math
import os
import queue
import socket
import threading
import time
from datetime import datetime, timedelta, timezone

import pygame
import requests
from spotipy.exceptions import SpotifyException

from common import (CACHE_PATH, SCOPES, granted_scopes, load_config, load_settings, make_client,
                    save_settings)
from discovery import LocalDevices, norm
import fonts
from i18n import LANGUAGES, month, set_language, tr, weekday
from lyrics import LyricsCache
from share import QrCache, spotify_link, wifi_payload
from weather import Weather

BG = (18, 18, 18)
PANEL = (42, 42, 42)
PANEL_ACTIVE = (64, 64, 64)
BUTTON = (84, 84, 84)      # knop binnen een rij
TEXT = (240, 240, 240)
MUTED = (160, 160, 160)
CLOCK = (130, 130, 130)
CLOCK_DIM = (95, 95, 95)
ACCENT = (30, 215, 96)     # wordt per beeld gezet uit de instelling "kleur"
APP_VERSION = "1.0"
TOAST = (80, 80, 80)

BASE_W, BASE_H = 800, 480   # rechthoekig ontwerp
ROUND_BASE = 480            # rond ontwerp: een cirkel van 480 breed
POLL_SECONDS = 2.0
FPS = 24                    # tijdens aanraken
CALM_FPS = 5                # als niemand het scherm aanraakt
MARQUEE_FPS = 24            # terwijl een lange titel schuift
# Zuinige stand (SPOTISCHERM_ZUINIG=1) voor trage Pi's zoals de Pi 1 of Zero: (aanraken, rust)
ECONOMY_FPS = (10, 2)
MARQUEE_PAUSE = 3.0         # seconden stilstaan voor een lange titel gaat schuiven
MARQUEE_SPEED = 40          # ontwerp-pixels per seconde
MARQUEE_GAP = 60            # ruimte tussen het einde en het opnieuw beginnen
FADE_SECONDS = 60          # slaaptimer: zo lang wordt het volume zachter
NIGHT_AWAKE_SECONDS = 30   # nachtmodus: zo lang blijft het scherm aan na een tik
EVENING_FADE = 60          # minuten voor de nacht waarin het scherm langzaam dimt
MORNING_FADE = 30          # minuten na de nacht waarin het weer normaal wordt
NIGHT_STYLES = ("uit", "zwart", "rood", "grijs")
NIGHT_STYLE_INFO = {
    "uit": "geen nachtmodus",
    "zwart": "'s avonds gedimd, 's nachts zwart",
    "rood": "'s avonds roder, 's nachts rode klok",
    "grijs": "'s avonds gedimd, 's nachts donkere klok",
}
# Vermenigvuldigkleur voor het hele scherm: bij volledig dimmen en voor de nachtklok.
DIM_TINT = {"zwart": (110, 110, 110), "rood": (170, 70, 70), "grijs": (110, 110, 110)}
NIGHT_TINT = {"rood": (150, 0, 0), "grijs": (75, 75, 75)}
SLEEP_OPTIONS = (15, 30, 45, 60, 90, 120)
DEVICES_REFRESH = 5        # apparatenlijst: elke zoveel seconden verversen
IDLE_OPTIONS = (1, 2, 5, 10, 15, 30, 60, 0)   # minuten tot de klok; 0 = nooit
NIGHT_STEP = 30            # nachttijden verschuiven per zoveel minuten
INFO_REFRESH = 5           # info-pagina: zo vaak (seconden) IP, wifi en temperatuur opnieuw lezen

ACCENTS = (("groen", "Groen", (30, 215, 96)), ("blauw", "Blauw", (64, 156, 255)),
           ("oranje", "Oranje", (255, 145, 48)), ("roze", "Roze", (255, 100, 170)),
           ("paars", "Paars", (170, 120, 255)), ("hoes", "Hoes", None))
ACCENT_COLORS = {key: color for key, _, color in ACCENTS}
# Draaien: graden met de klok mee, en hoe dat heet.
ROTATIONS = ((0, "Liggend"), (90, "Staand (rechtsom)"), (270, "Staand (linksom)"), (180, "Ondersteboven"))

KEY_ROWS = ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm")
KEY_BACKSPACE = "←"
# Toetsenbord per schermvorm: tekstveld, toetsmaat, rijen, onderste rij (annuleer, spatie, ok)
KEYBOARDS = {
    "rechthoek": {"field": (16, 12, 768, 60), "key": (70, 62), "gap": 6, "rows_y": (88, 156, 224, 292),
                  "bottom_y": 364, "bottom_h": 70, "bottom_w": (180, 360, 180), "size": 26},
    "rond": {"field": (100, 62, 280, 46), "key": (32, 48), "gap": 3, "rows_y": (120, 174, 228, 282),
             "bottom_y": 340, "bottom_h": 50, "bottom_w": (92, 110, 92), "size": 19},
    "staand": {"field": (16, -20, 448, 60), "key": (42, 64), "gap": 4, "rows_y": (70, 142, 214, 286),
               "bottom_y": 364, "bottom_h": 70, "bottom_w": (130, 172, 130), "size": 24},
}

# Plaats van lijsten en knoppen per schermvorm, in ontwerp-eenheden.
# Bij rond blijft alles binnen de cirkel (middelpunt 240,240, straal 240).
LAYOUTS = {
    "rechthoek": {
        "list_area": (16, 68, 768, 400), "row_h": 70, "title": (400, 32), "title_w": 500,
        "back": (16, 12, 120, 40), "action": (654, 12, 130, 40), "back_single": (16, 12, 120, 40),
        "pill_size": 20, "toast_y": 468, "toast_w": 760, "extra_w": 140, "extra_label": "+ Wachtrij",
    },
    "rond": {
        "list_area": (70, 88, 340, 308), "row_h": 64, "title": (240, 58), "title_w": 260,
        "back": (126, 404, 110, 40), "action": (244, 404, 110, 40), "back_single": (185, 404, 110, 40),
        "pill_size": 17, "toast_y": 392, "toast_w": 340, "extra_w": 48, "extra_label": "+",
    },
    # Staand gebruikt het 480-brede ontwerp van rond, maar het scherm loopt verder door:
    # zichtbaar van y=-160 tot y=640. Lijsten gebruiken die hele hoogte.
    "staand": {
        "list_area": (16, -44, 448, 616), "row_h": 70, "title": (240, -76), "title_w": 440,
        "back": (16, -150, 110, 44), "action": (354, -150, 110, 44), "back_single": (16, -150, 110, 44),
        "pill_size": 18, "toast_y": 624, "toast_w": 440, "extra_w": 120, "extra_label": "+ Wachtrij",
    },
}

# Lettertypes: (sleutel, naam, namen om te zoeken). Op de Pi installeert install.sh ze;
# op Windows vallen sommige terug op wat er wel is (bijv. Georgia of Consolas).
FONTS = (
    ("standaard", "Standaard", "dejavusans,freesans,arial"),
    ("roboto", "Roboto", "roboto"),
    ("opensans", "Open Sans", "opensans"),
    ("lato", "Lato", "lato"),
    ("comic", "Comic", "comicneue,comicsansms"),
    ("serif", "Serif", "dejavuserif,georgia,timesnewroman"),
    ("mono", "Mono", "dejavusansmono,consolas,couriernew"),
)
FONT_NAMES = {key: names for key, _, names in FONTS}
TYPES = {
    "Computer": "Computer", "Smartphone": "Telefoon", "Tablet": "Tablet",
    "Speaker": "Speaker", "TV": "Tv", "AVR": "Versterker",
    "CastAudio": "Cast-speaker", "CastVideo": "Chromecast",
    "GameConsole": "Spelcomputer", "Automobile": "Auto",
}
REPEAT_ORDER = ["off", "context", "track"]
LOCAL_KINDS = {"speaker": "Speaker", "group": "Speakergroep", "tv": "Tv", "connect": "Spotify Connect"}


def friendly_error(err):
    status = getattr(err, "http_status", None)
    if status == 404:
        return tr("Geen actief apparaat, kies er een via Apparaten")
    if status == 403:
        return tr("Niet toegestaan (Premium nodig, of het apparaat blokkeert dit)")
    if status == 429:
        return tr("Te veel verzoeken, even wachten")
    return tr("Spotify-fout {status}", status=status)


def pick_image(pb, small=False):
    item = (pb or {}).get("item") or {}
    images = (item.get("album") or {}).get("images") or item.get("images") or []
    if not images:
        return None
    # Normaal de grootste (meestal 640 px): op een groot of rond scherm wordt 300 px pixelig.
    # In de zuinige stand de kleinste die nog 300 px is: een trage Pi pakt die veel sneller uit.
    by_size = sorted(images, key=lambda i: i.get("width") or 0)
    if small:
        return next((i for i in by_size if (i.get("width") or 0) >= 300), by_size[-1])["url"]
    return by_size[-1]["url"]


def describe(item):
    if not item:
        return tr("Niks aan het spelen"), tr("Kies een apparaat of playlist"), ""
    if item.get("type") == "episode":
        return item["name"], (item.get("show") or {}).get("name", ""), ""
    artists = ", ".join(a["name"] for a in item.get("artists", []))
    return item["name"], artists, (item.get("album") or {}).get("name", "")


def track_info(item):
    _, subtitle, _ = describe(item)
    return " · ".join(x for x in (subtitle, fmt_ms(item.get("duration_ms") or 0)) if x)


def current_progress(pb, fetched_at):
    pos = pb.get("progress_ms") or 0
    if pb.get("is_playing"):
        pos += (time.monotonic() - fetched_at) * 1000
    duration = (pb.get("item") or {}).get("duration_ms") or 0
    return min(pos, duration) if duration else pos


def fmt_ms(ms):
    minutes, seconds = divmod(int(ms // 1000), 60)
    return f"{minutes}:{seconds:02d}"


def ago(iso):
    """'2026-09-28T19:10:00Z' -> '2 uur geleden'."""
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return ""
    minutes = (datetime.now(timezone.utc) - then).total_seconds() / 60
    if minutes < 60:
        return tr("{n} min geleden", n=max(1, int(minutes)))
    if minutes < 24 * 60:
        return tr("{n} uur geleden", n=int(minutes // 60))
    days = int(minutes // (24 * 60))
    return tr("gisteren") if days == 1 else tr("{n} dagen geleden", n=days)


def format_date(now):
    return tr("{weekday} {day} {month}", weekday=weekday(now.weekday()), day=now.day,
              month=month(now.month - 1))


def local_ip():
    """Het IP-adres van dit apparaat in het thuisnetwerk (er wordt niks verstuurd)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 9))
            return sock.getsockname()[0]
    except OSError:
        return None


def wifi_signal():
    """Signaalsterkte in dBm, "kabel" als er geen wifi is, of None als het onbekend is (bijv. Windows)."""
    try:
        lines = open("/proc/net/wireless", encoding="ascii").read().splitlines()[2:]
    except OSError:
        return None
    for line in lines:
        parts = line.split()
        if len(parts) > 3:
            return int(float(parts[3].rstrip(".")))
    return "kabel"


def cpu_temperature():
    try:
        return int(open("/sys/class/thermal/thermal_zone0/temp", encoding="ascii").read()) / 1000
    except (OSError, ValueError):
        return None


def duration_text(seconds):
    minutes = int(seconds // 60)
    if minutes < 60:
        return tr("{minutes} min", minutes=minutes)
    hours = minutes // 60
    if hours < 24:
        return tr("{h} uur {m} min", h=hours, m=minutes % 60)
    return tr("{d} dagen {h} uur", d=hours // 24, h=hours % 24)


def parse_night(start, end):
    """'23:00', '07:00' -> (1380, 420) in minuten na middernacht, of None (uit)."""
    try:
        return tuple(int(h) * 60 + int(m) for h, m in (v.strip().split(":") for v in (start, end)))
    except ValueError:
        return None


class Player:
    """Praat met Spotify in achtergrondthreads zodat het scherm nooit hapert."""

    def __init__(self, small_art=False):
        self.small_art = small_art
        # Heeft het opgeslagen token nog niet alle nieuwe toestemmingen (zoals recent
        # gespeeld)? Dan draaien we met wat er is, tot je opnieuw inlogt met auth.py.
        granted = granted_scopes()
        missing = set(SCOPES.split()) - granted
        self.can_recent = "user-read-recently-played" in granted
        self.sp = make_client(" ".join(sorted(granted)) if granted and missing else SCOPES)
        self.lock = threading.Lock()
        self.playback = None
        self.fetched_at = 0.0
        self.devices = None      # None = nog aan het laden
        self.playlists = None
        self.tracks = None       # lijst van (positie in playlist, nummer)
        self.tracks_for = None
        self.tracks_hidden = False
        self.queue_items = None
        self.search_results = None
        self.recent = None
        self.context_names = {}  # uri -> {naam, info}; {} als Spotify hem niet geeft
        self.last_ok = None
        self._search_for = None
        self.art_url = None
        self.art_image = None    # al uitgepakt, zodat het scherm niet hapert bij een nieuw nummer
        self.message = ""
        self.message_until = 0.0
        self.sleep_at = None
        self._fade_from = None
        self._hold_until = 0.0
        self._jobs = queue.Queue()
        self._wake = threading.Event()
        threading.Thread(target=self._poll_loop, daemon=True).start()
        threading.Thread(target=self._job_loop, daemon=True).start()

    def say(self, text, seconds=4):
        with self.lock:
            self.message = text
            self.message_until = time.monotonic() + seconds

    def snapshot(self):
        with self.lock:
            return self.playback, self.fetched_at

    def hold(self, seconds=1.5):
        """Even geen verse stand overnemen, zodat een net getoonde wijziging niet terugspringt."""
        self._hold_until = time.monotonic() + seconds

    def _poll_loop(self):
        while True:
            try:
                self._refresh()
            except Exception as err:  # wifi weg, token verlopen, ...
                print(f"Verversen mislukt: {err}", flush=True)
            try:
                self._sleep_tick()
            except Exception as err:
                print(f"Slaaptimer: {err}", flush=True)
            self._wake.wait(POLL_SECONDS)
            self._wake.clear()

    def _refresh(self):
        pb = self.sp.current_playback(additional_types="episode")
        self.last_ok = time.monotonic()
        if time.monotonic() < self._hold_until:
            return
        with self.lock:
            self.playback = pb
            self.fetched_at = time.monotonic()
        url = pick_image(pb, self.small_art)
        if url != self.art_url:
            image = None
            if url:
                try:
                    image = pygame.image.load(io.BytesIO(requests.get(url, timeout=8).content), "hoes.jpg")
                except pygame.error:
                    pass
            with self.lock:
                self.art_url, self.art_image = url, image

    def _job_loop(self):
        while True:
            fn, args = self._jobs.get()
            try:
                fn(*args)
            except SpotifyException as err:
                self.say(friendly_error(err))
            except requests.RequestException:
                self.say(tr("Geen verbinding met Spotify"))
            except Exception as err:
                print(f"Actie mislukt: {err}", flush=True)
                self.say(tr("Er ging iets mis"))
            time.sleep(0.4)  # Spotify heeft even nodig voor het de nieuwe stand meldt
            self._wake.set()

    def _run(self, fn, *args):
        self._jobs.put((fn, args))

    def _device(self):
        return (self.playback or {}).get("device") or {}

    # -- afspelen --

    def toggle(self):
        with self.lock:
            pb = self.playback
            device_id = self._device().get("id")
            playing = bool(pb and pb.get("is_playing"))
            if pb:  # meteen tonen, niet wachten op Spotify
                pb["progress_ms"] = current_progress(pb, self.fetched_at)
                pb["is_playing"] = not playing
                self.fetched_at = time.monotonic()
        self.hold()
        self._run(self.sp.pause_playback if playing else self.sp.start_playback, device_id)

    def next(self):
        self._run(self.sp.next_track, self._device().get("id"))

    def previous(self):
        # Zoals de Spotify-app: na 3 seconden eerst terug naar het begin van het nummer.
        pb, fetched_at = self.snapshot()
        if pb and pb.get("item") and current_progress(pb, fetched_at) > 3000:
            self.seek(0)
        else:
            self._run(self.sp.previous_track, self._device().get("id"))

    def seek(self, ms):
        with self.lock:
            if not self.playback:
                return
            self.playback["progress_ms"] = int(ms)
            self.fetched_at = time.monotonic()
            device_id = self._device().get("id")
        self.hold()
        self._run(self.sp.seek_track, int(ms), device_id)

    def set_volume(self, volume):
        with self.lock:
            device = self._device()
            if device.get("volume_percent") is None:
                return
            device["volume_percent"] = volume
        self.hold()
        self._run(self.sp.volume, volume, device.get("id"))

    def toggle_shuffle(self):
        with self.lock:
            pb = self.playback
            if not pb:
                return
            pb["shuffle_state"] = not pb.get("shuffle_state")
            state, device_id = pb["shuffle_state"], self._device().get("id")
        self.hold()
        self._run(self.sp.shuffle, state, device_id)

    def cycle_repeat(self):
        with self.lock:
            pb = self.playback
            if not pb:
                return
            now = pb.get("repeat_state")
            i = REPEAT_ORDER.index(now) if now in REPEAT_ORDER else 0
            pb["repeat_state"] = state = REPEAT_ORDER[(i + 1) % len(REPEAT_ORDER)]
            device_id = self._device().get("id")
        self.hold()
        self._run(self.sp.repeat, state, device_id)

    def play_context(self, uri, position=None, track_uri=None):
        """Speel een playlist/album/artiest, eventueel vanaf een bepaald nummer."""
        device_id = self._device().get("id")
        if not device_id:
            self.say(tr("Kies eerst een apparaat"))
            return False
        offset = ({"position": position} if position is not None
                  else {"uri": track_uri} if track_uri else None)
        self._run(self.sp.start_playback, device_id, uri, None, offset)
        return True

    def play_item(self, kind, item):
        if kind != "track":
            return self.play_context(item["uri"])
        # Een los nummer in de context van zijn album, zodat het album daarna doorspeelt.
        album = (item.get("album") or {}).get("uri")
        if album:
            return self.play_context(album, track_uri=item["uri"])
        device_id = self._device().get("id")
        if not device_id:
            self.say(tr("Kies eerst een apparaat"))
            return False
        self._run(self.sp.start_playback, device_id, None, [item["uri"]])
        return True

    def search(self, query):
        self.search_results, self._search_for = None, query
        self._run(self._search, query)

    def _search(self, query):
        res = self.sp.search(query, limit=10, type="track,artist,album,playlist")

        def pick(kind, n):
            return [i for i in ((res.get(kind + "s") or {}).get("items") or []) if i][:n]

        results = ([("track", t) for t in pick("track", 10)] + [("artist", a) for a in pick("artist", 3)]
                   + [("album", a) for a in pick("album", 3)] + [("playlist", p) for p in pick("playlist", 3)])
        if self._search_for == query:  # niet overschrijven als er intussen opnieuw gezocht is
            self.search_results = results

    # -- lijsten --

    def load_devices(self, keep=False):
        if not keep:
            self.devices = None
        self._run(self._load_devices)

    def _load_devices(self):
        self.devices = self.sp.devices().get("devices", [])

    def transfer(self, device_id):
        self._run(self.sp.transfer_playback, device_id, True)

    def load_recent(self):
        if self.can_recent:
            self._run(self._load_recent)

    def _load_recent(self):
        items = self.sp.current_user_recently_played(limit=50).get("items", [])
        tracks, seen, contexts = [], set(), []
        for entry in items:
            track, context_uri = entry.get("track"), (entry.get("context") or {}).get("uri")
            if track and track["uri"] not in seen and len(tracks) < 20:
                seen.add(track["uri"])
                tracks.append((track, entry.get("played_at")))
            if context_uri and context_uri not in contexts and len(contexts) < 6:
                contexts.append(context_uri)
        named = [c for c in map(self._context_info, contexts) if c]
        self.recent = {"contexts": named, "tracks": tracks}

    def _context_info(self, uri):
        """Naam en soort van een playlist/album/artiest; Spotify geeft die niet mee in 'recent'."""
        kind = uri.split(":")[1]
        try:
            if kind == "playlist":
                pl = self.sp.playlist(uri, fields="name,owner(display_name)")
                return {"uri": uri, "name": pl["name"], "info": "Playlist"}
            if kind == "album":
                album = self.sp.album(uri)
                artists = ", ".join(a["name"] for a in album.get("artists", []))
                return {"uri": uri, "name": album["name"], "info": f"Album · {artists}"}
            if kind == "artist":
                return {"uri": uri, "name": self.sp.artist(uri)["name"], "info": "Artiest"}
        except SpotifyException:
            pass
        return None  # bijv. Gelikete nummers: die kan de API niet als geheel afspelen

    def context_name(self, uri):
        """Naam van de playlist of het album dat speelt (voor Delen); None zolang hij laadt."""
        if uri not in self.context_names:
            self.context_names[uri] = None
            self._run(lambda: self.context_names.__setitem__(uri, self._context_info(uri) or {}))
        return self.context_names[uri]

    def load_playlists(self, keep=False):
        if not keep:
            self.playlists = None
        self._run(self._load_playlists)

    def _load_playlists(self):
        items = []
        page = self.sp.current_user_playlists(limit=50)
        while page and len(items) < 200:
            items.extend(p for p in page["items"] if p)
            page = self.sp.next(page) if page.get("next") else None
        self.playlists = items

    def load_tracks(self, playlist_id):
        self.tracks, self.tracks_for, self.tracks_hidden = None, playlist_id, False
        self._run(self._load_tracks, playlist_id)

    def _load_tracks(self, playlist_id):
        tracks = []
        try:
            page = self.sp.playlist_items(playlist_id, limit=100, additional_types=("track", "episode"))
        except SpotifyException as err:
            if err.http_status not in (403, 404):
                raise
            page = None
        if page is None:
            # Spotify toont sinds 2026 alleen nummers van playlists die van jou zijn
            if self.tracks_for == playlist_id:
                self.tracks, self.tracks_hidden = [], True
            return
        while page and len(tracks) < 500 and self.tracks_for == playlist_id:
            for i, entry in enumerate(page.get("items", [])):
                # Positie bewaren, ook als een nummer ontbreekt: Spotify start op positie.
                tracks.append((page["offset"] + i, entry.get("item") or entry.get("track")))
            self.tracks = list(tracks)  # alvast tonen terwijl de rest laadt
            page = self.sp.next(page) if page.get("next") else None

    def load_queue(self):
        self.queue_items = None
        self._run(self._load_queue)

    def _load_queue(self):
        self.queue_items = [i for i in (self.sp.queue() or {}).get("queue", []) if i]

    def add_to_queue(self, item):
        device_id = self._device().get("id")
        if not device_id:
            self.say(tr("Kies eerst een apparaat"))
            return
        self._run(self._add_to_queue, item, device_id)

    def _add_to_queue(self, item, device_id):
        self.sp.add_to_queue(item["uri"], device_id)
        self.say(tr("In de wachtrij: {name}", name=item["name"]))

    # -- slaaptimer --

    def sleep_left(self):
        sleep_at = self.sleep_at
        return None if sleep_at is None else max(0.0, sleep_at - time.monotonic())

    def set_sleep(self, minutes):
        fade_from = self._fade_from
        self._fade_from = None
        self.sleep_at = time.monotonic() + minutes * 60 if minutes else None
        if fade_from is not None:  # timer aangepast tijdens het zachter worden
            self.set_volume(fade_from)

    def _sleep_tick(self):
        left = self.sleep_left()
        if left is None:
            return
        with self.lock:
            pb = self.playback or {}
            device = pb.get("device") or {}
            playing = bool(pb.get("is_playing"))
        can_fade = device.get("supports_volume", True) and device.get("volume_percent") is not None

        if left <= 0:
            self.sleep_at = None
            fade_from, self._fade_from = self._fade_from, None
            if playing:
                self.sp.pause_playback(device.get("id"))
                with self.lock:
                    pb["is_playing"] = False
            if fade_from is not None:
                time.sleep(1)
                # Volume terugzetten, anders begint de volgende keer op fluistervolume.
                self.sp.volume(fade_from, device.get("id"))
            self.say(tr("Slaaptimer: welterusten"), 8)
        elif left <= FADE_SECONDS and playing and can_fade:
            if self._fade_from is None:
                self._fade_from = device["volume_percent"]
            target = int(self._fade_from * left / FADE_SECONDS)
            if target < device["volume_percent"]:
                self.sp.volume(target, device.get("id"))
                with self.lock:
                    device["volume_percent"] = target


class Screen:
    def __init__(self, display, settings, weather=None, round_screen=False, preview=False, local=None,
                 economy=False, framebuffer=None):
        self.display = display
        self.framebuffer = framebuffer  # plan B: zelf naar /dev/fb0 kopiëren i.p.v. via SDL tonen
        self.economy = economy
        self.base_round = round_screen
        self.preview = preview
        self.rotation = None
        self.started = time.monotonic()
        self._info, self._info_at = None, 0.0
        self.cover_accent = None
        self.p = None
        self.local = local
        self.devices_asked = 0.0
        self.settings = settings
        self.weather = weather
        self.fonts = {}
        self.text_cache = {}
        self.kb = None           # toetsenbord: {titel, tekst, knop, bij klaar, terug naar}
        self.search_query = ""
        self.view = "now"
        self.buttons = []
        self.sliders = []
        self.scroll = 0
        self.playlist = None
        self.playlist_scroll = 0
        self.art_key = None
        self.art_surf = None
        self.bg_surf = None
        self.cover_surf = None
        self.last_touch = time.monotonic()
        self.press = None
        self.dragging = False
        self.swallow = False
        self.drag = None         # [sleutel, 0..1, balk, bij loslaten, tijdens slepen]
        self.drag_sent = 0.0
        self.marquee_start = {}
        self.fade_masks = {}
        self.animating = False
        self.lyrics = LyricsCache()
        self.wrap_cache = {}
        self.fps, self.frame_ms = 0.0, 0.0
        self.show_fps = os.environ.get("SPOTISCHERM_TOON_FPS") == "1"
        self.qr = QrCache()
        self.share_tab = 0
        wifi_name = os.environ.get("GAST_WIFI_NAAM", "").strip()
        self.wifi = (wifi_name, os.environ.get("GAST_WIFI_WACHTWOORD", "").strip(),
                     os.environ.get("GAST_WIFI_BEVEILIGING", "WPA").strip()) if wifi_name else None
        self.apply_settings()

    def configure(self):
        """Canvas en schaal opnieuw bepalen, bijvoorbeeld na het draaien van het scherm."""
        self.rotation = self.settings["draaien"]
        dw, dh = self.display.get_size()
        self.w, self.h = (dh, dw) if self.rotation in (90, 270) else (dw, dh)
        # Gedraaid tekenen we op een eigen canvas en draaien dat bij het tonen.
        self.s = self.display if self.rotation == 0 else pygame.Surface((self.w, self.h))
        self.round = self.base_round
        self.shape = "rond" if self.round else "staand" if self.h > self.w else "rechthoek"
        self.compact = self.shape != "rechthoek"  # rond en staand delen het 480-brede ontwerp
        # Ontworpen op 800x480 (of 480 breed) en geschaald naar het echte scherm.
        base_w, base_h = (ROUND_BASE, ROUND_BASE) if self.compact else (BASE_W, BASE_H)
        self.cx = base_w // 2
        self.L = LAYOUTS[self.shape]
        self.k = min(self.w / base_w, self.h / base_h)
        self.ox = (self.w - base_w * self.k) / 2
        self.oy = (self.h - base_h * self.k) / 2
        # Op de pc laten we zien welk deel een rond scherm echt toont.
        self.mask = None
        if self.round and self.preview:
            self.mask = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            self.mask.fill((0, 0, 0, 255))
            pygame.draw.circle(self.mask, (0, 0, 0, 0), self.pt(240, 240), self.px(240))
        self.fonts.clear()
        self.text_cache.clear()
        self.art_key = "opnieuw"  # hoes opnieuw schalen voor de nieuwe maat
        self._info = None
        self.scroll = 0

    def present(self):
        if self.show_fps:
            self.text(f"{self.fps:.0f} fps · {self.frame_ms:.1f} ms", 14, ACCENT,
                      (self.w - self.px(8), self.px(6)), anchor="topright")
        if self.mask:
            self.s.blit(self.mask, (0, 0))
        if self.rotation:
            self.display.blit(pygame.transform.rotate(self.s, -self.rotation), (0, 0))
        if self.framebuffer:
            self.framebuffer.show(self.display)
        else:
            pygame.display.flip()

    def map_touch(self, pos):
        """Aanraking op het echte scherm -> punt op het (gedraaide) canvas."""
        x, y = pos
        dw, dh = self.display.get_size()
        if self.rotation == 90:
            return y, dw - 1 - x
        if self.rotation == 270:
            return dh - 1 - y, x
        if self.rotation == 180:
            return dw - 1 - x, dh - 1 - y
        return pos

    # -- schalen en tekenhulpjes --

    def px(self, n):
        return max(1, int(n * self.k))

    def pt(self, x, y):
        return int(self.ox + x * self.k), int(self.oy + y * self.k)

    def rect(self, x, y, w, h):
        return pygame.Rect(*self.pt(x, y), self.px(w), self.px(h))

    def font(self, size, bold, family=None):
        family = family or self.settings["lettertype"]
        key = (size, bold, family)
        if key not in self.fonts:
            # Zelf zoeken i.p.v. pygame's fc-list (te traag op een Pi 1); anders het ingebouwde lettertype.
            path = fonts.find(family, bold) or fonts.find("standaard", bold)
            self.fonts[key] = pygame.font.Font(path, self.px(size))
        return self.fonts[key]

    @staticmethod
    def font_installed(family):
        return fonts.find(family) is not None

    def text(self, s, size, color, pos, anchor="topleft", max_w=None, bold=False, family=None):
        key = (s, size, color, max_w, bold, family or self.settings["lettertype"])
        surf = self.text_cache.get(key)
        if surf is None:
            f = self.font(size, bold, family)
            if max_w and f.size(s)[0] > max_w:
                while s and f.size(s + "…")[0] > max_w:
                    s = s[:-1]
                s = s.rstrip() + "…"
            surf = f.render(s, True, color)
            if len(self.text_cache) > 400:
                self.text_cache.clear()
            self.text_cache[key] = surf
        r = surf.get_rect(**{anchor: pos})
        self.s.blit(surf, r)
        return r

    def rendered(self, s, size, color, bold=False):
        """De tekst als plaatje, zonder afkappen (bewaard voor hergebruik)."""
        key = (s, size, color, None, bold, self.settings["lettertype"])
        surf = self.text_cache.get(key)
        if surf is None:
            surf = self.font(size, bold).render(s, True, color)
            self.text_cache[key] = surf
        return surf

    def marquee(self, s, size, color, pos, anchor="topleft", max_w=None, bold=False):
        """Als text(), maar een te lange tekst schuift als een lichtkrant in plaats van af te kappen."""
        if self.economy:  # schuiven kost een trage Pi te veel; gewoon afkappen
            return self.text(s, size, color, pos, anchor, max_w, bold)
        surf = self.rendered(s, size, color, bold)
        if not max_w or surf.get_width() <= max_w:
            return self.text(s, size, color, pos, anchor, bold=bold)
        box = pygame.Rect(0, 0, max_w, surf.get_height())
        setattr(box, anchor, pos)
        # Elke tekst begint met stilstaan; een nieuw nummer begint dus weer vooraan.
        start = self.marquee_start.setdefault((s, size), time.monotonic())
        if len(self.marquee_start) > 30:
            self.marquee_start = {(s, size): start}
        loop = surf.get_width() + self.px(MARQUEE_GAP)
        speed = self.px(MARQUEE_SPEED)
        t = (time.monotonic() - start) % (MARQUEE_PAUSE + loop / speed)
        offset = 0 if t < MARQUEE_PAUSE else int((t - MARQUEE_PAUSE) * speed)
        if offset:
            self.animating = True
        strip = pygame.Surface(box.size, pygame.SRCALPHA)
        strip.blit(surf, (-offset, 0))
        strip.blit(surf, (loop - offset, 0))  # het begin komt er weer achteraan
        # Zacht vervagen aan de rand; links alleen tijdens het schuiven, anders vervaagt het begin.
        strip.blit(self.fade_mask(box.size, left=bool(offset)), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.s.blit(strip, box)
        return box

    def fade_mask(self, size, left):
        key = (size, left)
        if key not in self.fade_masks:
            w, h = size
            mask = pygame.Surface(size, pygame.SRCALPHA)
            mask.fill((255, 255, 255, 255))
            fade = min(self.px(28), w // 4)
            for x in range(fade):
                color = (255, 255, 255, int(255 * x / fade))
                pygame.draw.line(mask, color, (w - 1 - x, 0), (w - 1 - x, h))
                if left:
                    pygame.draw.line(mask, color, (x, 0), (x, h))
            self.fade_masks[key] = mask
        return self.fade_masks[key]

    def wrap(self, text, size, max_w):
        """Verdeelt tekst over regels die niet breder zijn dan max_w pixels."""
        key = (text, size, max_w, self.settings["lettertype"])
        if key in self.wrap_cache:
            return self.wrap_cache[key]
        if len(self.wrap_cache) > 500:
            self.wrap_cache.clear()
        self.wrap_cache[key] = lines = self._wrap(text, size, max_w)
        return lines

    def _wrap(self, text, size, max_w):
        f = self.font(size, False)
        lines = []
        for part in text.split("\n"):
            line = ""
            for word in part.split():
                candidate = f"{line} {word}".strip()
                if line and f.size(candidate)[0] > max_w:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        return lines

    def paragraph(self, text, size, color, center, max_w):
        """Tekst over meerdere regels, gecentreerd."""
        lines = self.wrap(text, size, max_w)
        step = self.font(size, False).get_linesize()
        for i, line in enumerate(lines):
            y = center[1] + step * (i - (len(lines) - 1) / 2)
            self.text(line, size, color, (center[0], int(y)), anchor="center", max_w=max_w)

    def pill(self, r, label, action, active=False, size=20, bg=PANEL, fg=TEXT, family=None):
        pygame.draw.rect(self.s, ACCENT if active else bg, r, border_radius=r.h // 2)
        # Lange woorden (andere taal of lettertype) eerst iets kleiner maken, pas daarna afkappen.
        room = r.w - self.px(16)
        while size > 12 and self.font(size, False, family).size(label)[0] > room:
            size -= 1
        self.text(label, size, BG if active else fg, r.center, anchor="center", max_w=room, family=family)
        self.buttons.append((r, action))

    def round_button(self, x, y, radius, icon, action, filled=False, lit=False):
        c, r = self.pt(x, y), self.px(radius)
        if filled:
            pygame.draw.circle(self.s, ACCENT, c, r)
        elif icon in ("prev", "next", "search", "gear", "qr"):
            pygame.draw.circle(self.s, PANEL, c, r)
        color = BG if filled else ACCENT if lit else TEXT
        self.icon(icon, c, r, color)
        if lit:
            pygame.draw.circle(self.s, ACCENT, (c[0], c[1] + int(r * 1.05)), max(2, int(r * 0.12)))
        hit = max(r, self.px(30))
        self.buttons.append((pygame.Rect(c[0] - hit, c[1] - hit, 2 * hit, 2 * hit), action))

    def icon(self, kind, c, r, color):
        x, y = c
        lw = max(2, int(r * 0.13))
        if kind == "play":
            pts = [(x - r * 0.3, y - r * 0.45), (x - r * 0.3, y + r * 0.45), (x + r * 0.5, y)]
            pygame.draw.polygon(self.s, color, pts)
        elif kind == "pause":
            bw, bh = r * 0.22, r * 0.9
            for dx in (-r * 0.22, r * 0.22):
                pygame.draw.rect(self.s, color, pygame.Rect(x + dx - bw / 2, y - bh / 2, bw, bh))
        elif kind in ("next", "prev"):
            d = 1 if kind == "next" else -1
            pts = [(x - d * r * 0.4, y - r * 0.4), (x - d * r * 0.4, y + r * 0.4), (x + d * r * 0.25, y)]
            pygame.draw.polygon(self.s, color, pts)
            bar_x = x + d * r * 0.3 - (r * 0.12 if d < 0 else 0)
            pygame.draw.rect(self.s, color, pygame.Rect(bar_x, y - r * 0.4, r * 0.12, r * 0.8))
        elif kind == "search":
            pygame.draw.circle(self.s, color, (x - r * 0.12, y - r * 0.12), r * 0.34, lw)
            pygame.draw.line(self.s, color, (x + r * 0.13, y + r * 0.13), (x + r * 0.45, y + r * 0.45), lw + 1)
        elif kind == "gear":
            pygame.draw.circle(self.s, color, (x, y), r * 0.3, lw)
            for i in range(8):
                a = i * math.pi / 4
                inner, outer = r * 0.36, r * 0.52
                pygame.draw.line(self.s, color, (x + math.cos(a) * inner, y + math.sin(a) * inner),
                                 (x + math.cos(a) * outer, y + math.sin(a) * outer), lw + 2)
        elif kind == "qr":
            # Drie hoekjes zoals op een QR-code, en een blokje rechtsonder.
            s, gap = r * 0.3, r * 0.08
            for dx, dy in ((-1, -1), (1, -1), (-1, 1)):
                box = pygame.Rect(0, 0, s, s)
                box.center = (x + dx * (s / 2 + gap), y + dy * (s / 2 + gap))
                pygame.draw.rect(self.s, color, box, max(2, lw - 1))
            dot = pygame.Rect(0, 0, s * 0.45, s * 0.45)
            dot.center = (x + s / 2 + gap, y + s / 2 + gap)
            pygame.draw.rect(self.s, color, dot)
        elif kind == "shuffle":
            a, b = r * 0.55, r * 0.38
            pygame.draw.line(self.s, color, (x - a, y + b), (x + a * 0.7, y - b), lw)
            pygame.draw.line(self.s, color, (x - a, y - b), (x + a * 0.7, y + b), lw)
            for ey in (y - b, y + b):
                pygame.draw.polygon(self.s, color, [(x + a + r * 0.1, ey), (x + a * 0.55, ey - r * 0.2),
                                                    (x + a * 0.55, ey + r * 0.2)])
        else:  # repeat, repeat1
            box = pygame.Rect(0, 0, r * 1.3, r * 0.85)
            box.center = (x, y)
            pygame.draw.rect(self.s, color, box, lw, border_radius=int(r * 0.3))
            pygame.draw.polygon(self.s, color, [(x + r * 0.05, box.top - r * 0.22),
                                                (x + r * 0.05, box.top + r * 0.22), (x + r * 0.35, box.top)])
            if kind == "repeat1":
                self.text("1", max(8, int(r * 0.55 / self.k)), color, (x, y), anchor="center", bold=True)

    def slider(self, key, bar, frac, color, on_release, on_drag=None):
        frac = max(0.0, min(1.0, frac))
        pygame.draw.rect(self.s, PANEL, bar, border_radius=bar.h // 2)
        done = bar.copy()
        done.w = int(bar.w * frac)
        pygame.draw.rect(self.s, color, done, border_radius=bar.h // 2)
        grabbed = self.drag and self.drag[0] == key
        pygame.draw.circle(self.s, TEXT, (bar.x + done.w, bar.centery), self.px(11 if grabbed else 8))
        hit = bar.inflate(self.px(24), self.px(40))
        to_frac = lambda pos: max(0.0, min(1.0, (pos[0] - bar.x) / bar.w))
        self.sliders.append((key, hit.collidepoint, to_frac, on_release, on_drag))

    def ring(self, key, frac, color, on_release):
        """Voortgang als ring langs de rand van een rond scherm, met de klok mee vanaf boven."""
        c, radius, width = self.pt(240, 240), self.px(226), self.px(8)
        pygame.draw.circle(self.s, PANEL, c, radius + width // 2, width)
        frac = max(0.0, min(1.0, frac))
        points = lambda rr, a: (c[0] + math.sin(a) * rr, c[1] - math.cos(a) * rr)
        if frac > 0:
            steps = max(2, int(180 * frac))
            angles = [2 * math.pi * frac * i / steps for i in range(steps + 1)]
            outer = [points(radius + width / 2, a) for a in angles]
            inner = [points(radius - width / 2, a) for a in reversed(angles)]
            pygame.draw.polygon(self.s, color, outer + inner)
        grabbed = self.drag and self.drag[0] == key
        pygame.draw.circle(self.s, TEXT, points(radius, 2 * math.pi * frac), self.px(12 if grabbed else 9))

        inner_r, outer_r = self.px(212), self.px(250)
        contains = lambda pos: inner_r <= math.hypot(pos[0] - c[0], pos[1] - c[1]) <= outer_r
        to_frac = lambda pos: (math.atan2(pos[0] - c[0], c[1] - pos[1]) % (2 * math.pi)) / (2 * math.pi)
        self.sliders.append((key, contains, to_frac, on_release, None))

    def drag_value(self, key):
        return self.drag[1] if self.drag and self.drag[0] == key else None

    def update_art(self):
        with self.p.lock:
            url, image = self.p.art_url, self.p.art_image
        if self.art_key == url:
            return
        self.art_key, self.art_surf, self.bg_surf, self.cover_surf = url, None, None, None
        self.cover_accent = None
        if not image:
            return
        img = image if image.get_bitsize() >= 24 else image.convert(24)
        self.cover_accent = self.accent_from(img)
        # Zuinig: gewoon schalen (veel sneller) en geen achtergrond uit de hoes. Na het schalen
        # omzetten naar het schermformaat, zodat tekenen snel is (ook bij een 16-bits scherm).
        scale = pygame.transform.scale if self.economy else pygame.transform.smoothscale
        if self.shape == "staand":
            size = self.px(400)
            self.art_surf = scale(img, (size, size))
        if self.compact:
            side = max(self.w, self.h)
            full = scale(img, (side, side))
            if not self.economy:
                # De hoes vult gedimd de hele cirkel; tekst en knoppen staan erop.
                big = full.copy()
                big.fill((70, 70, 70), special_flags=pygame.BLEND_MULT)
                self.bg_surf = pygame.Surface((self.w, self.h))
                self.bg_surf.blit(big, ((self.w - side) // 2, (self.h - side) // 2))
            # Voor het rustscherm: dezelfde hoes, maar niet gedimd.
            self.cover_surf = pygame.Surface((self.w, self.h))
            self.cover_surf.blit(full, ((self.w - side) // 2, (self.h - side) // 2))
        else:
            size = self.px(384)
            self.art_surf = scale(img, (size, size))
            self.cover_surf = scale(img, (self.px(432), self.px(432)))
            if not self.economy:
                self.bg_surf = self.gradient(pygame.transform.average_color(img))
        # Alles in het formaat van het canvas, zodat elk beeld zonder omzetten getekend wordt.
        self.art_surf, self.bg_surf, self.cover_surf = (
            surf.convert(self.s) if surf else None for surf in (self.art_surf, self.bg_surf, self.cover_surf))

    @staticmethod
    def accent_from(img):
        """Een heldere kleur uit de hoes, voor knoppen en balken. None bij een grijze hoes."""
        c = pygame.Color(*pygame.transform.average_color(img)[:3])
        h, s, v, _ = c.hsva
        if s < 12:
            return None
        c.hsva = (h, max(55, min(s * 1.4, 90)), 90, 100)
        return c.r, c.g, c.b

    def gradient(self, rgb):
        """Donkere tint van de hoes bovenaan, die naar onderen overloopt in zwart."""
        c = pygame.Color(*rgb[:3])
        h, s, v, _ = c.hsva
        c.hsva = (h, min(100, s * 1.3), min(v, 38), 100)
        top = (c.r, c.g, c.b)
        surf = pygame.Surface((self.w, self.h))
        fade = self.h * 0.8
        for y in range(self.h):
            t = min(1.0, y / fade)
            surf.fill(tuple(int(a + (b - a) * t) for a, b in zip(top, BG)), (0, y, self.w, 1))
        return surf

    # -- toestand --

    def is_idle(self):
        if self.view == "lyrics":
            pb, _ = self.p.snapshot()
            if pb and pb.get("is_playing"):
                return False  # meelezen: niet naar de klok springen
        return time.monotonic() - self.last_touch > self.idle_after

    def in_night(self):
        if not self.night:
            return False
        start, end = self.night
        now = datetime.now()
        minute = now.hour * 60 + now.minute
        return start <= minute < end if start < end else minute >= start or minute < end

    def is_dark(self):
        return self.in_night() and time.monotonic() - self.last_touch > NIGHT_AWAKE_SECONDS

    def dim_level(self):
        """0 = normaal, 1 = volledig gedimd. Loopt geleidelijk op voor de nacht en af erna."""
        if not self.night:
            return 0.0
        if self.in_night():
            return 1.0
        start, end = self.night
        now = datetime.now()
        minute = now.hour * 60 + now.minute + now.second / 60
        until_night = (start - minute) % (24 * 60)
        since_night = (minute - end) % (24 * 60)
        if until_night <= EVENING_FADE:
            return 1 - until_night / EVENING_FADE
        if since_night <= MORNING_FADE:
            return 1 - since_night / MORNING_FADE
        return 0.0

    def tint(self, color, amount=1.0):
        """Vermenigvuldigt het hele scherm met een kleur: wit laat alles zoals het is."""
        mult = tuple(int(255 + (c - 255) * amount) for c in color)
        self.s.fill(mult, special_flags=pygame.BLEND_MULT)

    def resting(self):
        return self.is_dark() or self.is_idle()

    # -- schermen --

    def draw(self):
        global ACCENT
        self.buttons, self.sliders = [], []
        self.animating = False
        self.update_art()
        choice = self.settings["kleur"]
        ACCENT = (self.cover_accent if choice == "hoes" else ACCENT_COLORS.get(choice)) or ACCENT_COLORS["groen"]
        style = self.settings["nacht_stijl"]
        if self.is_dark():
            self.s.fill((0, 0, 0))
            if style in NIGHT_TINT:  # zeer gedimde klok in plaats van zwart
                self.draw_clock()
                self.tint(NIGHT_TINT[style])
        elif self.is_idle():
            self.s.fill(BG)
            pb, _ = self.p.snapshot()
            playing = bool(pb and pb.get("is_playing") and pb.get("item"))
            self.update_art()
            if self.settings["rust_scherm"] == "hoes" and playing and self.cover_surf:
                self.draw_cover(pb["item"])
            else:
                self.draw_clock()
        else:
            self.update_art()
            if self.bg_surf:
                self.s.blit(self.bg_surf, (0, 0))
            else:
                self.s.fill(BG)
            views = {"devices": self.draw_devices, "playlists": self.draw_playlists,
                     "tracks": self.draw_tracks, "queue": self.draw_queue, "timer": self.draw_timer,
                     "menu": self.draw_menu, "keyboard": self.draw_keyboard, "search": self.draw_search,
                     "settings": self.draw_settings, "recent": self.draw_recent,
                     "set_weer": self.draw_set_weer, "set_rust": self.draw_set_rust,
                     "set_nacht": self.draw_set_nacht, "set_font": self.draw_set_font,
                     "set_taal": self.draw_set_taal, "set_kleur": self.draw_set_kleur,
                     "set_scherm": self.draw_set_scherm, "info": self.draw_info,
                     "lyrics": self.draw_lyrics, "share": self.draw_share}
            now_view = {"rond": self.draw_now_round, "staand": self.draw_now_portrait}.get(self.shape, self.draw_now)
            views.get(self.view, now_view)()
            self.draw_toast()
        if not self.is_dark():
            dim = self.dim_level()
            if dim > 0 and style in DIM_TINT:
                self.tint(DIM_TINT[style], dim)
        self.present()

    def draw_message(self, title, lines):
        self.s.fill(BG)
        max_w = self.px(340 if self.compact else 760)
        self.paragraph(title, 26, TEXT, self.pt(self.cx, 180), max_w)
        self.paragraph("\n".join(lines), 18, MUTED, self.pt(self.cx, 270), max_w)
        self.present()

    def draw_clock(self):
        # (y, lettergrootte) voor tijd, datum, weer, regen
        if self.compact:
            spots, max_w = ((190, 110), (272, 24), (322, 20), (356, 17)), 380
        else:
            spots, max_w = ((175, 150), (280, 28), (350, 24), (392, 20)), 760
        now = datetime.now()
        date = format_date(now)
        lines = [(now.strftime("%H:%M"), CLOCK, True), (date, CLOCK, False)]
        if self.weather and self.weather.summary:
            lines += [(self.weather.summary, CLOCK, False), (self.weather.rain, CLOCK_DIM, False)]
        for (text, color, bold), (y, size) in zip(lines, spots):
            self.text(text, size, color, self.pt(self.cx, y), anchor="center", max_w=self.px(max_w), bold=bold)

        # Speelt er muziek? Dan klein onderaan wat er speelt.
        pb, _ = self.p.snapshot()
        if pb and pb.get("is_playing") and pb.get("item"):
            title, subtitle, _ = describe(pb["item"])
            y, size, w = (410, 16, 300) if self.compact else (446, 18, 700)
            self.text(f"♪ {title} · {subtitle}", size, CLOCK_DIM, self.pt(self.cx, y), anchor="center",
                      max_w=self.px(w))

    def draw_now_round(self):
        pb, fetched_at = self.p.snapshot()
        item = (pb or {}).get("item")
        device = (pb or {}).get("device") or {}
        playing = bool(pb and pb.get("is_playing"))
        title, subtitle, _ = describe(item)
        cx = self.cx

        if item:
            duration = item.get("duration_ms") or 1
            dragged = self.drag_value("seek")
            pos = dragged * duration if dragged is not None else current_progress(pb, fetched_at)
            self.ring("seek", pos / duration, ACCENT, lambda f: self.p.seek(f * duration))
            self.text(f"{fmt_ms(pos)} / {fmt_ms(duration)}", 16, MUTED, self.pt(cx, 254), anchor="center")

        name = device.get("name")
        self.pill(self.rect(130, 88, 220, 36), tr("Op: {name}", name=name) if name else tr("Kies apparaat"),
                  self.open_devices, size=17)
        left = self.p.sleep_left()
        if left:
            self.text(tr("Slaaptimer {minutes} min", minutes=math.ceil(left / 60)), 15, ACCENT, self.pt(cx, 146), anchor="center")
        self.marquee(title, 28, TEXT, self.pt(cx, 186), anchor="center", max_w=self.px(330), bold=True)
        self.marquee(subtitle, 20, MUTED, self.pt(cx, 222), anchor="center", max_w=self.px(320))

        repeat = (pb or {}).get("repeat_state", "off")
        self.round_button(cx - 150, 302, 22, "shuffle", self.p.toggle_shuffle,
                          lit=bool(pb and pb.get("shuffle_state")))
        self.round_button(cx - 78, 302, 28, "prev", self.p.previous)
        self.round_button(cx, 302, 40, "pause" if playing else "play", self.p.toggle, filled=True)
        self.round_button(cx + 78, 302, 28, "next", self.p.next)
        self.round_button(cx + 150, 302, 22, "repeat1" if repeat == "track" else "repeat",
                          self.p.cycle_repeat, lit=repeat != "off")

        volume = device.get("volume_percent")
        if device.get("supports_volume", True) and volume is not None:
            dragged = self.drag_value("volume")
            if dragged is not None:
                volume = round(dragged * 100)
            self.text(tr("Volume {volume}%", volume=volume), 15, MUTED, self.pt(cx, 350), anchor="center")
            set_volume = lambda f: self.p.set_volume(round(f * 100))
            self.slider("volume", self.rect(150, 370, 180, 8), volume / 100, TEXT,
                        set_volume, on_drag=set_volume)

        self.pill(self.rect(180, 404, 120, 36), tr("Menu"), self.open_menu, size=18)

    def draw_now_portrait(self):
        """Staand scherm: de hoes groot bovenaan, bediening eronder."""
        pb, fetched_at = self.p.snapshot()
        item = (pb or {}).get("item")
        device = (pb or {}).get("device") or {}
        playing = bool(pb and pb.get("is_playing"))
        title, subtitle, _ = describe(item)
        cx = self.cx

        name = device.get("name")
        self.pill(self.rect(16, -150, 250, 44), tr("Op: {name}", name=name) if name else tr("Kies apparaat"),
                  self.open_devices, size=18)
        self.round_button(298, -128, 20, "search", self.open_search)
        self.round_button(350, -128, 20, "gear", self.open_settings)
        self.pill(self.rect(384, -150, 80, 44), tr("Menu"), self.open_menu, size=18)
        left = self.p.sleep_left()
        if left:
            self.text(tr("Slaaptimer {minutes} min", minutes=math.ceil(left / 60)), 15, ACCENT,
                      self.pt(cx, -86), anchor="center")

        art_rect = self.rect(40, -64, 400, 400)
        if self.art_surf:
            self.s.blit(self.art_surf, art_rect)
        else:
            pygame.draw.rect(self.s, PANEL, art_rect, border_radius=self.px(12))
            self.text("♪", 140, MUTED, art_rect.center, anchor="center")
        self.lyrics_button(art_rect)

        self.marquee(title, 28, TEXT, self.pt(cx, 368), anchor="center", max_w=self.px(440), bold=True)
        self.marquee(subtitle, 20, MUTED, self.pt(cx, 402), anchor="center", max_w=self.px(440))
        if item:
            duration = item.get("duration_ms") or 1
            dragged = self.drag_value("seek")
            pos = dragged * duration if dragged is not None else current_progress(pb, fetched_at)
            self.slider("seek", self.rect(40, 432, 400, 6), pos / duration, ACCENT,
                        lambda f: self.p.seek(f * duration))
            self.text(fmt_ms(pos), 15, MUTED, self.pt(40, 448))
            self.text(fmt_ms(duration), 15, MUTED, self.pt(440, 448), anchor="topright")

        repeat = (pb or {}).get("repeat_state", "off")
        self.round_button(cx - 160, 510, 24, "shuffle", self.p.toggle_shuffle,
                          lit=bool(pb and pb.get("shuffle_state")))
        self.round_button(cx - 82, 510, 30, "prev", self.p.previous)
        self.round_button(cx, 510, 44, "pause" if playing else "play", self.p.toggle, filled=True)
        self.round_button(cx + 82, 510, 30, "next", self.p.next)
        self.round_button(cx + 160, 510, 24, "repeat1" if repeat == "track" else "repeat",
                          self.p.cycle_repeat, lit=repeat != "off")

        volume = device.get("volume_percent")
        if device.get("supports_volume", True) and volume is not None:
            dragged = self.drag_value("volume")
            if dragged is not None:
                volume = round(dragged * 100)
            self.text(tr("Volume {volume}%", volume=volume), 15, MUTED, self.pt(cx, 566), anchor="center")
            set_volume = lambda f: self.p.set_volume(round(f * 100))
            self.slider("volume", self.rect(60, 590, 360, 8), volume / 100, TEXT, set_volume, on_drag=set_volume)

    def lyrics_button(self, art_rect):
        """Tik op de hoes (of het knopje erop) voor de songtekst."""
        self.buttons.append((art_rect, self.open_lyrics))
        r = pygame.Rect(0, 0, self.px(120), self.px(36))
        r.bottomright = (art_rect.right - self.px(10), art_rect.bottom - self.px(10))
        self.pill(r, tr("Songtekst"), self.open_lyrics, size=15, bg=BG)

    def draw_menu(self):
        self.text(tr("Menu"), 24, TEXT, self.pt(self.cx, 80), anchor="center", bold=True)
        left = self.p.sleep_left()
        items = [(tr("Apparaten"), self.open_devices), (tr("Playlists"), self.open_playlists),
                 (tr("Wachtrij"), self.open_queue),
                 (tr("Timer {minutes}m", minutes=math.ceil(left / 60)) if left else tr("Slaaptimer"),
                  self.open_timer),
                 (tr("Zoeken"), self.open_search), (tr("Instellingen"), self.open_settings),
                 (tr("Recent"), self.open_recent), (tr("Songtekst"), self.open_lyrics),
                 (tr("Delen"), self.open_share)]
        for i, (label, action) in enumerate(items):
            alone = i == len(items) - 1 and len(items) % 2  # laatste knop alleen op zijn rij: midden
            r = self.rect(167 if alone else 90 + (i % 2) * 154, 104 + (i // 2) * 59, 146, 52)
            self.pill(r, label, action, size=18, active=i == 3 and bool(left))
        self.pill(self.rect(*self.L["back_single"]), tr("‹ Terug"), self.back, size=self.L["pill_size"])

    def draw_now(self):
        pb, fetched_at = self.p.snapshot()
        item = (pb or {}).get("item")
        device = (pb or {}).get("device") or {}
        playing = bool(pb and pb.get("is_playing"))
        title, subtitle, album = describe(item)

        name = device.get("name")
        self.pill(self.rect(16, 12, 196, 40), tr("Op: {name}", name=name) if name else tr("Kies apparaat"), self.open_devices)
        self.round_button(238, 32, 20, "search", self.open_search)
        self.round_button(292, 32, 20, "qr", self.open_share)
        self.round_button(346, 32, 20, "gear", self.open_settings)
        left = self.p.sleep_left()
        self.pill(self.rect(386, 12, 126, 40), tr("Timer {minutes}m", minutes=math.ceil(left / 60)) if left else tr("Timer"),
                  self.open_timer, active=bool(left))
        self.pill(self.rect(522, 12, 124, 40), tr("Wachtrij"), self.open_queue)
        self.pill(self.rect(656, 12, 124, 40), tr("Playlists"), self.open_playlists)

        art_rect = self.rect(24, 72, 384, 384)
        if self.art_surf:
            self.s.blit(self.art_surf, art_rect)
        else:
            pygame.draw.rect(self.s, PANEL, art_rect, border_radius=self.px(12))
            self.text("♪", 140, MUTED, art_rect.center, anchor="center")
        self.lyrics_button(art_rect)

        x0, cw = 440, 336
        self.marquee(title, 30, TEXT, self.pt(x0, 84), max_w=self.px(cw), bold=True)
        self.marquee(subtitle, 22, MUTED, self.pt(x0, 128), max_w=self.px(cw))
        self.marquee(album, 18, MUTED, self.pt(x0, 162), max_w=self.px(cw))

        if item:
            duration = item.get("duration_ms") or 1
            dragged = self.drag_value("seek")
            pos = dragged * duration if dragged is not None else current_progress(pb, fetched_at)
            self.slider("seek", self.rect(x0, 214, cw, 6), pos / duration, ACCENT,
                        lambda f: self.p.seek(f * duration))
            self.text(fmt_ms(pos), 16, MUTED, self.pt(x0, 232))
            self.text(fmt_ms(duration), 16, MUTED, self.pt(x0 + cw, 232), anchor="topright")

        cx = x0 + cw // 2
        repeat = (pb or {}).get("repeat_state", "off")
        self.round_button(cx - 146, 310, 26, "shuffle", self.p.toggle_shuffle,
                          lit=bool(pb and pb.get("shuffle_state")))
        self.round_button(cx - 80, 310, 30, "prev", self.p.previous)
        self.round_button(cx, 310, 44, "pause" if playing else "play", self.p.toggle, filled=True)
        self.round_button(cx + 80, 310, 30, "next", self.p.next)
        self.round_button(cx + 146, 310, 26, "repeat1" if repeat == "track" else "repeat",
                          self.p.cycle_repeat, lit=repeat != "off")

        volume = device.get("volume_percent")
        if device.get("supports_volume", True) and volume is not None:
            dragged = self.drag_value("volume")
            if dragged is not None:
                volume = round(dragged * 100)
            self.text(tr("Volume {volume}%", volume=volume), 16, MUTED, self.pt(cx, 394), anchor="midtop")
            set_volume = lambda f: self.p.set_volume(round(f * 100))
            self.slider("volume", self.rect(x0 + 8, 430, cw - 16, 8), volume / 100, TEXT,
                        set_volume, on_drag=set_volume)

    def draw_list(self, title, rows, empty_text, button=None, back=None):
        """rows: (titel, info, actief, bij tikken, optioneel: actie voor de wachtrijknop)."""
        L = self.L
        size = L["pill_size"]
        back_rect = L["back"] if button else L["back_single"]
        self.pill(self.rect(*back_rect), tr("‹ Terug"), back or self.back, size=size)
        self.text(title, 24, TEXT, self.pt(*L["title"]), anchor="center", bold=True, max_w=self.px(L["title_w"]))
        if button:
            self.pill(self.rect(*L["action"]), *button, size=size)

        area = self.rect(*L["list_area"])
        if rows is None:
            self.text(tr("Laden…"), 22, MUTED, area.center, anchor="center")
            return
        if not rows:
            self.paragraph(empty_text, 20, MUTED, area.center, area.w)
            return

        row_h = self.px(L["row_h"])
        extra_w = self.px(L["extra_w"])
        self.scroll = max(0, min(self.scroll, len(rows) * row_h - area.h))
        self.s.set_clip(area)
        for i, row in enumerate(rows):
            label, sub, active, action = row[:4]
            extra = row[4] if len(row) > 4 else None
            dim = len(row) > 5 and row[5]
            top = area.y + i * row_h - self.scroll
            if top + row_h < area.y or top > area.bottom:
                continue
            r = pygame.Rect(area.x, top, area.w, row_h - self.px(8))
            pygame.draw.rect(self.s, PANEL_ACTIVE if active else PANEL, r, border_radius=self.px(12))
            if active:
                pygame.draw.rect(self.s, ACCENT, (r.x, r.y + self.px(12), self.px(5), r.h - self.px(24)))
            inner = r.w - self.px(40) - (extra_w + self.px(20) if extra else 0)
            color = ACCENT if active else MUTED if dim else TEXT
            self.text(label, 22, color, (r.x + self.px(20), r.y + self.px(8)),
                      max_w=inner, bold=active)
            self.text(sub, 16, MUTED, (r.x + self.px(20), r.y + self.px(36)), max_w=inner)
            if action:
                self.buttons.append((r.clip(area), action))
            if extra:
                er = pygame.Rect(0, 0, extra_w, self.px(40))
                er.midright = (r.right - self.px(12), r.centery)
                self.pill(er, tr(L["extra_label"]), extra, size=18 if len(L["extra_label"]) > 1 else 26,
                          bg=BUTTON)
                self.buttons[-1] = (er.clip(area), extra)
        self.s.set_clip(None)

    def draw_devices(self):
        # Zolang de lijst openstaat regelmatig verversen: kies je een speaker op je
        # telefoon, dan wordt hij hier vanzelf bedienbaar.
        if time.monotonic() - self.devices_asked > DEVICES_REFRESH:
            self.devices_asked = time.monotonic()
            self.p.load_devices(keep=True)
        devices = self.p.devices
        rows = None
        if devices is not None:
            rows = [(d["name"], self.device_info(d), d.get("is_active"),
                     lambda d=d: self.pick_device(d)) for d in devices]
            known = {norm(d["name"]) for d in devices}
            local = [d for d in (self.local.snapshot() if self.local else []) if not d["aliases"] & known]
            order = {"speaker": 0, "group": 1, "tv": 2, "connect": 3}
            for d in sorted(local, key=lambda d: (order[d["kind"]], d["name"].casefold())):
                rows.append((d["name"], tr("{kind} · nog niet actief bij Spotify", kind=tr(LOCAL_KINDS[d["kind"]])),
                             False,
                             lambda d=d: self.explain_local(d), None, True))
        self.draw_list(tr("Kies een apparaat"), rows,
                       tr("Niks gevonden.\nOpen Spotify op de speaker of telefoon en tik Vernieuw."),
                       button=(tr("Vernieuw"), self.p.load_devices))

    def explain_local(self, d):
        self.p.say(tr("Kies ‘{name}’ één keer in de Spotify-app op je telefoon. "
                      "Daarna kun je hem hier bedienen.", name=d["name"]), 7)

    def draw_playlists(self):
        playlists = self.p.playlists
        rows = None
        if playlists is not None:
            rows = []
            for pl in playlists:
                total = (pl.get("items") or pl.get("tracks") or {}).get("total")
                owner = (pl.get("owner") or {}).get("display_name") or ""
                info = " · ".join(x for x in (tr("{n} nummers", n=total) if total is not None else "", owner) if x)
                rows.append((pl["name"], info, False, lambda pl=pl: self.pick_playlist(pl)))
        self.draw_list(tr("Playlists"), rows, tr("Geen playlists gevonden."),
                       button=(tr("Recent"), self.open_recent))

    def draw_tracks(self):
        pl = self.playlist
        rows = None
        if self.p.tracks_for == pl["id"] and self.p.tracks is not None:
            pb, _ = self.p.snapshot()
            playing_uri = ((pb or {}).get("item") or {}).get("uri")
            rows = []
            for pos, item in self.p.tracks:
                if not item:
                    continue
                rows.append((item["name"], track_info(item), item.get("uri") == playing_uri,
                             lambda pos=pos: self.pick_track(pos),
                             lambda item=item: self.p.add_to_queue(item)))
        empty = (tr("Spotify toont alleen de nummers van playlists die van jou zijn.\n"
                    "Tik op Speel alles om hem toch te starten.") if self.p.tracks_hidden
                 else tr("Deze playlist is leeg."))
        self.draw_list(pl["name"], rows, empty, button=(tr("Speel alles"), self.play_playlist),
                       back=self.back_to_playlists)

    def draw_queue(self):
        items = self.p.queue_items
        rows = None
        if items is not None:
            pb, _ = self.p.snapshot()
            now_item = (pb or {}).get("item")
            rows = [(now_item["name"], tr("Nu · {info}", info=track_info(now_item)), True, None)] if now_item else []
            rows += [(it["name"], track_info(it), False, None) for it in items]
        self.draw_list(tr("Hierna"), rows, tr("De wachtrij is leeg.\nZet nummers erin via Playlists."),
                       button=(tr("Vernieuw"), self.p.load_queue))

    def draw_timer(self):
        L = self.L
        self.pill(self.rect(*L["back_single"]), tr("‹ Terug"), self.back, size=L["pill_size"])
        self.text(tr("Slaaptimer"), 24, TEXT, self.pt(*L["title"]), anchor="center", bold=True)
        left = self.p.sleep_left()
        end = datetime.now() + timedelta(seconds=left or 0)
        if self.compact:
            status = tr("Stopt om {time}", time=f"{end:%H:%M}") if left else tr("Wanneer stoppen?")
            status_pos, max_w = (240, 108), 320
            grid = lambda i: (84 + (i % 3) * 108, 136 + (i // 3) * 80, 96, 64)
            off_rect, size = (170, 306, 140, 48), 17
        else:
            status = (tr("De muziek stopt om {time}. De laatste minuut wordt hij zachter.", time=f"{end:%H:%M}")
                      if left else tr("Na hoeveel minuten moet de muziek stoppen?"))
            status_pos, max_w = (400, 110), 760
            grid = lambda i: (100 + (i % 3) * 210, 160 + (i // 3) * 100, 180, 76)
            off_rect, size = (300, 380, 200, 60), 26
        self.text(status, 20, MUTED, self.pt(*status_pos), anchor="center", max_w=self.px(max_w))
        for i, minutes in enumerate(SLEEP_OPTIONS):
            self.pill(self.rect(*grid(i)), tr("{minutes} min", minutes=minutes), lambda m=minutes: self.pick_sleep(m), size=size)
        if left:
            self.pill(self.rect(*off_rect), tr("Timer uit"), lambda: self.pick_sleep(None), size=20)

    def key(self, r, label, action, size, bg=PANEL, fg=TEXT):
        pygame.draw.rect(self.s, bg, r, border_radius=self.px(8))
        self.text(label, size, fg, r.center, anchor="center", max_w=r.w - self.px(6))
        self.buttons.append((r, action))

    def draw_keyboard(self):
        kb, g = self.kb, KEYBOARDS[self.shape]
        size = g["size"]

        field = self.rect(*g["field"])
        pygame.draw.rect(self.s, PANEL, field, border_radius=self.px(12))
        pad = self.px(16)
        if kb["text"]:
            f, shown = self.font(size, False), kb["text"]
            while shown and f.size(shown)[0] > field.w - 3 * pad:  # lange tekst: het einde tonen
                shown = shown[1:]
            r = self.text(shown, size, TEXT, (field.x + pad, field.centery), anchor="midleft")
            cursor_x = r.right + self.px(2)
        else:
            self.text(kb["title"], size, MUTED, (field.x + pad, field.centery), anchor="midleft")
            cursor_x = field.x + pad
        pygame.draw.rect(self.s, ACCENT, (cursor_x, field.y + self.px(10), self.px(3), field.h - self.px(20)))

        kw, kh = g["key"]
        for keys, y in zip(KEY_ROWS, g["rows_y"]):
            row = [(k, kw) for k in keys]
            if keys is KEY_ROWS[-1]:
                row.append((KEY_BACKSPACE, kw * 1.5))
            x = self.cx - (sum(w for _, w in row) + g["gap"] * (len(row) - 1)) / 2
            for k, w in row:
                action = self.kb_backspace if k == KEY_BACKSPACE else (lambda k=k: self.kb_type(k))
                self.key(self.rect(x, y, w, kh), k, action, size)
                x += w + g["gap"]

        widths = g["bottom_w"]
        x = self.cx - (sum(widths) + 2 * g["gap"]) / 2
        bottom = [(tr("Annuleer"), self.kb_cancel, PANEL, TEXT),
                  (tr("spatie"), lambda: self.kb_type(" "), PANEL, MUTED),
                  (kb["label"], self.kb_done, ACCENT, BG)]
        for (label, action, bg, fg), w in zip(bottom, widths):
            self.key(self.rect(x, g["bottom_y"], w, g["bottom_h"]), label, action, size - 2, bg, fg)
            x += w + g["gap"]

    def draw_search(self):
        results = self.p.search_results
        rows = None
        if results is not None:
            pb, _ = self.p.snapshot()
            playing_uri = ((pb or {}).get("item") or {}).get("uri")
            rows = []
            for kind, item in results:
                play = lambda kind=kind, item=item: self.pick_result(kind, item)
                if kind == "track":
                    rows.append((item["name"], tr("Nummer · {info}", info=track_info(item)), item.get("uri") == playing_uri,
                                 play, lambda item=item: self.p.add_to_queue(item)))
                elif kind == "artist":
                    rows.append((item["name"], tr("Artiest"), False, play))
                elif kind == "album":
                    artists = ", ".join(a["name"] for a in item.get("artists", []))
                    rows.append((item["name"], tr("Album · {artists}", artists=artists), False, play))
                else:
                    owner = (item.get("owner") or {}).get("display_name") or ""
                    rows.append((item["name"], tr("Playlist · {owner}", owner=owner) if owner else tr("Playlist"),
                                 False, play))
        self.draw_list(f"‘{self.search_query}’", rows, tr("Niks gevonden.\nProbeer een andere zoekterm."),
                       button=(tr("Opnieuw"), self.open_search))

    def draw_settings(self):
        """Instellingen als menu: per onderdeel een eigen pagina."""
        s = self.settings
        if s["weer_plaats"]:
            info = self.weather.summary if self.weather else None
            weather = f"{s['weer_plaats']} · {info}" if info else s["weer_plaats"]
        else:
            weather = tr("Uit")
        idle = tr("na {minutes} min", minutes=f"{s['idle_min']:g}") if s["idle_min"] else tr("nooit")
        rest = f"{tr(s['rust_scherm'].capitalize())} · {idle}"
        night = (tr("Uit") if s["nacht_stijl"] == "uit"
                 else f"{tr(s['nacht_stijl'].capitalize())} · {s['nacht_van']}–{s['nacht_tot']}")
        font = next(tr(label) for key, label, _ in FONTS if key == s["lettertype"])
        rows = [(tr("Weer"), weather, False, lambda: self.open_setting("set_weer")),
                (tr("Rustscherm"), rest, False, lambda: self.open_setting("set_rust")),
                (tr("Nachtmodus"), night, False, lambda: self.open_setting("set_nacht")),
                (tr("Lettertype"), font, False, lambda: self.open_setting("set_font")),
                (tr("Kleur"), tr(next(label for key, label, _ in ACCENTS if key == s["kleur"])), False,
                 lambda: self.open_setting("set_kleur")),
                (tr("Taal"), LANGUAGES[s["taal"]], False, lambda: self.open_setting("set_taal")),
                (tr("Scherm"), tr(dict(ROTATIONS)[s["draaien"]]), False, lambda: self.open_setting("set_scherm")),
                (tr("Info"), self.system_info()[0][1], False, lambda: self.open_setting("info"))]
        self.draw_list(tr("Instellingen"), rows, "")

    def setting_page(self, title):
        L = self.L
        self.pill(self.rect(*L["back_single"]), tr("‹ Terug"), self.open_settings, size=L["pill_size"])
        self.text(tr(title), 24, TEXT, self.pt(*L["title"]), anchor="center", bold=True)

    def choices(self, options, current, pick, box, cols, size):
        """Rij of raster van keuzeknoppen; de gekozen staat groen."""
        x0, y0, w, h, gap = box
        for i, (value, label) in enumerate(options):
            r = self.rect(x0 + (i % cols) * (w + gap), y0 + (i // cols) * (h + gap), w, h)
            self.pill(r, label, lambda v=value: pick(v), active=value == current, size=size)

    def draw_set_weer(self):
        self.setting_page("Weer")
        s, w = self.settings, self.weather
        if self.compact:
            spots, max_w, sizes = (240, 142, 180, 210), 320, (24, 16, 15)
            change, clear = (140, 250, 200, 52), (170, 318, 140, 44)
        else:
            spots, max_w, sizes = (400, 130, 180, 214), 700, (30, 20, 18)
            change, clear = (250, 262, 300, 60), (300, 340, 200, 50)
        cx, y_place, y_info, y_rain = spots
        if s["weer_plaats"]:
            self.text(s["weer_plaats"], sizes[0], TEXT, self.pt(cx, y_place), anchor="center",
                      max_w=self.px(max_w), bold=True)
            info = (w.error or w.summary or tr("Weer ophalen…")) if w else ""
            self.text(info, sizes[1], MUTED, self.pt(cx, y_info), anchor="center", max_w=self.px(max_w))
            if w and w.summary and w.rain:
                self.text(w.rain, sizes[2], MUTED, self.pt(cx, y_rain), anchor="center", max_w=self.px(max_w))
            self.pill(self.rect(*change), tr("Plaats wijzigen"), self.edit_place, size=sizes[2] + 2)
            self.pill(self.rect(*clear), tr("Geen weer"), lambda: self.change_setting("weer_plaats", ""),
                      size=sizes[2], fg=MUTED)
        else:
            self.paragraph(tr("Geen weer bij de klok. Kies een plaats om het weer te zien."), sizes[1], MUTED,
                           self.pt(cx, y_info - 20), self.px(max_w))
            self.pill(self.rect(*change), tr("Plaats kiezen"), self.edit_place, size=sizes[2] + 2)

    def draw_set_rust(self):
        self.setting_page("Rustscherm")
        s = self.settings
        what = [("hoes", tr("Hoes")), ("klok", tr("Klok"))]
        # Op het ronde scherm is er geen ruimte voor "min"; de kop noemt het al.
        minutes = [(m, (str(m) if self.compact else tr("{minutes} min", minutes=m)) if m else tr("Nooit"))
                   for m in IDLE_OPTIONS]
        explain = (tr("De albumhoes groot als er muziek speelt, anders de klok.") if s["rust_scherm"] == "hoes"
                   else tr("Altijd de klok met het weer."))
        set_what = lambda v: self.change_setting("rust_scherm", v)
        set_idle = lambda v: self.change_setting("idle_min", v)
        if self.compact:
            self.text(tr("Wat laten zien"), 15, MUTED, self.pt(240, 98), anchor="center")
            self.choices(what, s["rust_scherm"], set_what, (130, 112, 106, 48, 8), 2, 18)
            self.text(explain, 13, MUTED, self.pt(240, 180), anchor="center", max_w=self.px(300))
            self.text(tr("Na hoeveel minuten"), 15, MUTED, self.pt(240, 204), anchor="center")
            self.choices(minutes, s["idle_min"], set_idle, (91, 218, 70, 46, 6), 4, 16)
        else:
            self.text(tr("Wat laten zien"), 18, MUTED, self.pt(400, 92), anchor="center")
            self.choices(what, s["rust_scherm"], set_what, (220, 108, 172, 56, 16), 2, 22)
            self.text(explain, 16, MUTED, self.pt(400, 190), anchor="center", max_w=self.px(700))
            self.text(tr("Na hoeveel minuten zonder aanraken"), 18, MUTED, self.pt(400, 232), anchor="center")
            self.choices(minutes, s["idle_min"], set_idle, (90, 254, 145, 56, 12), 4, 20)

    def draw_set_nacht(self):
        self.setting_page("Nachtmodus")
        s = self.settings
        styles = [(v, tr(v.capitalize())) for v in NIGHT_STYLES]
        on = s["nacht_stijl"] != "uit"
        set_style = lambda v: self.change_setting("nacht_stijl", v)
        if self.compact:
            self.choices(styles, s["nacht_stijl"], set_style, (126, 94, 110, 44, 8), 2, 17)
            self.text(tr(NIGHT_STYLE_INFO[s["nacht_stijl"]]), 13, MUTED, self.pt(240, 208), anchor="center",
                      max_w=self.px(300))
            rows = ((250, "Vanaf", "nacht_van"), (306, "Tot", "nacht_tot"))
            label_x, step, value_x, size = 104, (212, 38, 44), 298, 18
        else:
            self.choices(styles, s["nacht_stijl"], set_style, (70, 84, 152, 54, 12), 4, 20)
            self.text(tr(NIGHT_STYLE_INFO[s["nacht_stijl"]]), 18, MUTED, self.pt(400, 172), anchor="center",
                      max_w=self.px(700))
            rows = ((252, "Vanaf", "nacht_van"), (330, "Tot", "nacht_tot"))
            label_x, step, value_x, size = 180, (360, 56, 58), 480, 26
        color = TEXT if on else MUTED
        minus_x, btn_w, btn_h = step
        for y, label, key in rows:
            self.text(tr(label), size, color, self.pt(label_x, y), anchor="midleft")
            minus = self.rect(minus_x, y - btn_h / 2, btn_w, btn_h)
            plus = self.rect(2 * value_x - minus_x - btn_w, y - btn_h / 2, btn_w, btn_h)
            self.pill(minus, "–", lambda k=key: self.step_night(k, -1), size=size + 2, bg=BUTTON)
            self.pill(plus, "+", lambda k=key: self.step_night(k, 1), size=size + 2, bg=BUTTON)
            self.text(s[key], size, color, self.pt(value_x, y), anchor="center", bold=on)

    def draw_set_font(self):
        """Elke keuze staat in zijn eigen letter, zodat je ziet wat je kiest."""
        self.setting_page("Lettertype")
        if self.compact:
            tile = lambda i: (88 + (i % 2) * 156, 92 + (i // 2) * 54, 150, 44)
            size, sample_y, sample_size, sample_w = 17, 360, 15, 300
        else:
            tile = lambda i: (50 + (i % 2) * 360, 78 + (i // 2) * 62, 340, 52)
            size, sample_y, sample_size, sample_w = 22, 356, 22, 700
        for i, (key, label, _) in enumerate(FONTS):
            r = self.rect(*tile(i))
            if self.font_installed(key):
                self.pill(r, tr(label), lambda k=key: self.change_setting("lettertype", k),
                          active=key == self.settings["lettertype"], size=size, family=key)
            else:
                self.pill(r, f"{tr(label)} ({tr('niet geïnstalleerd')})",
                          lambda: self.p.say(tr("niet geïnstalleerd")), size=size - 4, fg=MUTED)
        self.text(f"{tr('Tekst ziet er zo uit')} · 12:34 · ♪", sample_size, MUTED, self.pt(self.cx, sample_y),
                  anchor="center", max_w=self.px(sample_w))

    def draw_set_taal(self):
        self.setting_page("Taal")
        if self.compact:
            tile, size = (lambda i: (140, 120 + i * 64, 200, 52)), 20
        else:
            tile, size = (lambda i: (85 + i * 215, 150, 200, 64)), 24
        for i, (code, name) in enumerate(LANGUAGES.items()):
            self.pill(self.rect(*tile(i)), name, lambda c=code: self.change_setting("taal", c),
                      active=code == self.settings["taal"], size=size)

    def draw_set_kleur(self):
        """Elke kleur staat als knop in die kleur; de gekozen krijgt een witte rand."""
        self.setting_page("Kleur")
        if self.compact:
            tile, size, note = (lambda i: (100 + (i % 2) * 146, 110 + (i // 2) * 66, 134, 52)), 17, (368, 13, 300)
        else:
            tile, size, note = (lambda i: (70 + (i % 3) * 230, 110 + (i // 3) * 96, 200, 64)), 22, (340, 17, 700)
        for i, (key, label, color) in enumerate(ACCENTS):
            r = self.rect(*tile(i))
            bg = color or self.cover_accent or PANEL
            self.pill(r, tr(label), lambda k=key: self.change_setting("kleur", k), size=size, bg=bg,
                      fg=BG if (color or self.cover_accent) else TEXT)
            if key == self.settings["kleur"]:
                pygame.draw.rect(self.s, TEXT, r.inflate(self.px(10), self.px(10)), self.px(3),
                                 border_radius=r.h // 2 + self.px(5))
        y, note_size, max_w = note
        self.text(tr("Hoes: de kleur past zich aan elk nummer aan."), note_size, MUTED, self.pt(self.cx, y),
                  anchor="center", max_w=self.px(max_w))

    def draw_set_scherm(self):
        self.setting_page("Scherm")
        if self.compact:
            tile, size, note = (lambda i: (120, 100 + i * 56, 240, 46)), 17, (348, 13, 300)
        else:
            tile, size, note = (lambda i: (90 + (i % 2) * 320, 110 + (i // 2) * 80, 300, 60)), 20, (300, 17, 700)
        for i, (degrees, label) in enumerate(ROTATIONS):
            self.pill(self.rect(*tile(i)), tr(label), lambda d=degrees: self.change_setting("draaien", d),
                      active=degrees == self.settings["draaien"], size=size)
        y, note_size, max_w = note
        self.paragraph(tr("Draait het beeld en de aanraking. Staat alles op zijn kop? Kies dan de andere "
                          "staande stand."), note_size, MUTED, self.pt(self.cx, y), self.px(max_w))

    def system_info(self):
        """Regels voor de info-pagina; IP, wifi en temperatuur lezen we niet elk beeld opnieuw."""
        now = time.monotonic()
        if self._info and now - self._info_at < INFO_REFRESH:
            return self._info
        ip = local_ip()
        signal = wifi_signal()
        if signal == "kabel":
            wifi = tr("via kabel")
        elif signal is None:
            wifi = tr("onbekend")
        else:
            quality = "goed" if signal >= -60 else "redelijk" if signal >= -70 else "zwak"
            wifi = f"{signal} dBm · {tr(quality)}"
        temp = cpu_temperature()
        last_ok = self.p.last_ok
        spotify = tr("verbonden") if last_ok and now - last_ok < 30 else tr("geen verbinding")
        dw, dh = self.display.get_size()
        shape = {"rechthoek": "liggend", "staand": "staand", "rond": "rond"}[self.shape]
        self._info = [
            (tr("IP-adres"), ip or tr("geen netwerk")),
            (tr("Naam"), f"{socket.gethostname()}.local"),
            (tr("Wifi"), wifi),
            (tr("Temperatuur"), f"{temp:.0f} °C" if temp is not None else tr("onbekend")),
            ("Spotify", spotify),
            (tr("Scherm"), f"{dw}×{dh} · {tr(shape)}"),
            (tr("Draait al"), duration_text(now - self.started)),
            (tr("Versie"), APP_VERSION),
            (tr("Zuinige stand"), tr("aan") if self.economy else tr("uit")),
        ]
        self._info_at = now
        return self._info

    def draw_info(self):
        self.setting_page("Info")
        lines = self.system_info()
        if self.compact:
            for i, (label, value) in enumerate(lines):
                self.text(f"{label}: {value}", 15, TEXT if i == 0 else MUTED, self.pt(self.cx, 100 + i * 32),
                          anchor="center", max_w=self.px(320), bold=i == 0)
            return
        for i, (label, value) in enumerate(lines):
            y = 96 + i * 42
            self.text(label, 20, MUTED, self.pt(360, y), anchor="midright")
            self.text(value, 20, TEXT, self.pt(384, y), anchor="midleft", max_w=self.px(400), bold=i == 0)

    def draw_cover(self, item):
        """Rustscherm met de albumhoes groot en de tijd erbij."""
        title, subtitle, _ = describe(item)
        now = datetime.now()
        date = format_date(now)
        if self.compact:
            self.s.blit(self.cover_surf, (0, 0))
            labels = (((180, 58, 120, 46), [(now.strftime("%H:%M"), 24, TEXT, True)]),
                      ((100, 372, 280, 62), [(title, 18, TEXT, True), (subtitle, 14, MUTED, False)]))
            for (x, y, w, h), lines in labels:
                r = self.rect(x, y, w, h)
                pygame.draw.rect(self.s, BG, r, border_radius=r.h // 2)
                step = r.h / (len(lines) + 1)
                for i, (text, size, color, bold) in enumerate(lines):
                    self.marquee(text, size, color, (r.centerx, int(r.y + step * (i + 1))), anchor="center",
                              max_w=r.w - self.px(24), bold=bold)
            return
        if self.bg_surf:
            self.s.blit(self.bg_surf, (0, 0))
        self.s.blit(self.cover_surf, self.rect(24, 24, 432, 432))
        cx, max_w = 628, self.px(290)
        self.text(now.strftime("%H:%M"), 88, TEXT, self.pt(cx, 150), anchor="center", bold=True)
        self.text(date, 20, MUTED, self.pt(cx, 222), anchor="center", max_w=max_w)
        self.marquee(title, 24, TEXT, self.pt(cx, 300), anchor="center", max_w=max_w, bold=True)
        self.marquee(subtitle, 20, MUTED, self.pt(cx, 336), anchor="center", max_w=max_w)
        if self.weather and self.weather.summary:
            self.text(self.weather.summary, 16, MUTED, self.pt(cx, 410), anchor="center", max_w=max_w)

    def draw_recent(self):
        recent = self.p.recent
        rows = None
        if not self.p.can_recent:
            rows = []
        elif recent is not None:
            rows = [(c["name"], c["info"], False, lambda c=c: self.pick_context(c["uri"]))
                    for c in recent["contexts"]]
            for track, played_at in recent["tracks"]:
                info = " · ".join(x for x in (describe(track)[1], ago(played_at)) if x)
                rows.append((track["name"], info, False, lambda t=track: self.pick_result("track", t),
                             lambda t=track: self.p.add_to_queue(t)))
        empty = (tr("Log één keer opnieuw in bij Spotify om dit te zien: .venv/bin/python app/auth.py "
                    "en herstart daarna de app.") if not self.p.can_recent else tr("Nog niks gespeeld."))
        self.draw_list(tr("Recent"), rows, empty, button=(tr("Playlists"), self.open_playlists))

    def draw_lyrics(self):
        """Songtekst: bij een meelopende tekst staat de huidige regel groot in het midden."""
        L = self.L
        self.pill(self.rect(*L["back_single"]), tr("‹ Terug"), self.back, size=L["pill_size"])
        self.text(tr("Songtekst"), 24, TEXT, self.pt(*L["title"]), anchor="center", bold=True)
        pb, fetched_at = self.p.snapshot()
        item = (pb or {}).get("item")
        if self.shape == "rond":
            area, big, small, max_w = self.rect(70, 88, 340, 304), 22, 17, self.px(320)
        elif self.shape == "staand":
            area, big, small, max_w = self.rect(24, -46, 432, 676), 26, 19, self.px(430)
        else:
            area, big, small, max_w = self.rect(40, 64, 720, 400), 30, 22, self.px(700)
            self.text("lrclib.net", 13, CLOCK_DIM, self.pt(784, 470), anchor="bottomright")
        if not item:
            self.text(tr("Niks aan het spelen"), small, MUTED, area.center, anchor="center")
            return
        lyr = self.lyrics.get(item)
        if lyr is None:
            message = tr("Songtekst laden…")
        elif lyr.instrumental:
            message = "♪ " + tr("Instrumentaal") + " ♪"
        elif not lyr.found:
            message = tr("Geen songtekst gevonden")
        else:
            message = None
        if message:
            self.paragraph(message, small, MUTED, area.center, max_w)
            return

        self.s.set_clip(area)
        if lyr.lines:
            self.draw_synced(lyr, current_progress(pb, fetched_at) / 1000, area, big, small, max_w)
        else:
            # Alleen een gewone tekst: laten scrollen met je vinger.
            f = self.font(small, False)
            lines = [line for part in lyr.plain.splitlines() for line in (self.wrap(part, small, max_w) or [""])]
            step = f.get_linesize()
            self.scroll = max(0, min(self.scroll, len(lines) * step - area.h + self.px(20)))
            for i, line in enumerate(lines):
                y = area.y + self.px(10) + i * step - self.scroll
                if area.y - step < y < area.bottom:
                    self.text(line, small, TEXT, (area.centerx, y), anchor="midtop", max_w=max_w)
        self.s.set_clip(None)

    def draw_synced(self, lyr, seconds, area, big, small, max_w):
        i = lyr.index_at(seconds + 0.3)  # iets vooruit: Spotify meldt de stand met een kleine vertraging
        gap = self.px(12)
        cur_h = self.font(big, True).get_linesize()
        other_h = self.font(small, False).get_linesize()
        current = self.wrap(lyr.lines[i][1] if i >= 0 else "♪", big, int(max_w * 0.92))
        y = area.centery - len(current) * cur_h // 2
        for n, line in enumerate(current):
            self.text(line, big, TEXT, (area.centerx, y + n * cur_h), anchor="midtop", bold=True)
        fade = lambda d: MUTED if d == 1 else (120, 120, 120) if d <= 3 else (85, 85, 85)
        # Regels hierna, naar beneden tot het vlak vol is.
        below = y + len(current) * cur_h + gap
        for j in range(i + 1, len(lyr.lines)):
            if below > area.bottom:
                break
            for line in self.wrap(lyr.lines[j][1], small, max_w):
                self.text(line, small, fade(j - i), (area.centerx, below), anchor="midtop")
                below += other_h
            below += gap
        # Regels hiervoor, naar boven.
        above = y - gap
        for j in range(i - 1, -1, -1):
            block = self.wrap(lyr.lines[j][1], small, max_w)
            above -= len(block) * other_h
            if above + len(block) * other_h < area.y:
                break
            for n, line in enumerate(block):
                self.text(line, small, fade(i - j), (area.centerx, above + n * other_h), anchor="midtop")
            above -= gap

    def share_items(self):
        """Wat je kunt delen: (kop, regels eronder, tekst in de QR-code)."""
        pb, _ = self.p.snapshot()
        item = (pb or {}).get("item")
        items = []
        if item and spotify_link(item.get("uri")):
            title, subtitle, _ = describe(item)
            kop = tr("Deze aflevering") if item.get("type") == "episode" else tr("Dit nummer")
            items.append((kop, [title, subtitle], spotify_link(item["uri"])))
        uri = ((pb or {}).get("context") or {}).get("uri")
        if item and spotify_link(uri):
            kind = uri.split(":")[1]
            kop = {"playlist": tr("Deze playlist"), "album": tr("Dit album"),
                   "artist": tr("Deze artiest"), "show": tr("Deze podcast")}.get(kind, tr("Deze lijst"))
            info = self.p.context_name(uri)
            name = info.get("name", "") if info is not None else "…"
            items.append((kop, [name], spotify_link(uri)))
        if self.wifi:
            name, password, security = self.wifi
            lines = [name, tr("Wachtwoord: {password}", password=password) if password else tr("Geen wachtwoord")]
            items.append((tr("Wifi"), lines, wifi_payload(name, password, security)))
        return items

    def draw_share(self):
        L = self.L
        self.pill(self.rect(*L["back_single"]), tr("‹ Terug"), self.back, size=L["pill_size"])
        self.text(tr("Delen"), 24, TEXT, self.pt(*L["title"]), anchor="center", bold=True)
        max_w = self.px(320 if self.round else 440 if self.compact else 600)
        if not self.qr.available:
            self.paragraph(tr("QR-codes maken lukt nog niet. Voer op de Pi opnieuw bash install.sh uit "
                              "en herstart de app."), 20, MUTED, self.pt(self.cx, 240), max_w)
            return
        items = self.share_items()
        if not items:
            self.paragraph(tr("Er speelt niks om te delen. Zet GAST_WIFI_NAAM in config.env "
                              "voor een QR-code van je gast-wifi."), 20, MUTED, self.pt(self.cx, 240), max_w)
            return
        self.share_tab = min(self.share_tab, len(items) - 1)
        if self.compact:
            # (QR-maat, bovenkant, tekst, tabbladen y, breedte, hoogte, tekstbreedte)
            size, top, text_y, tabs_y, tab_w, tab_h, text_w = {
                "rond": (170, 84, 270, 342, 100, 40, 280),
                "staand": (380, -40, 370, 470, 140, 56, 440)}[self.shape]
            kop, lines, data = items[self.share_tab]
            self.share_card(kop, lines, data, self.cx, top, size, text_y, text_w)
            if len(items) > 1:
                gap = 8
                x0 = self.cx - (len(items) * tab_w + (len(items) - 1) * gap) // 2
                for i, (kop, _, _) in enumerate(items):
                    self.pill(self.rect(x0 + i * (tab_w + gap), tabs_y, tab_w, tab_h), kop,
                              lambda i=i: setattr(self, "share_tab", i), active=i == self.share_tab, size=16)
            return
        size = {1: 300, 2: 280}.get(len(items), 220)
        slot = 768 / len(items)
        for i, (kop, lines, data) in enumerate(items):
            self.share_card(kop, lines, data, int(16 + slot * (i + 0.5)), 72, size, 72 + size + 24, int(slot) - 24)
        if not self.wifi:
            self.text(tr("Tip: zet GAST_WIFI_NAAM in config.env voor een QR-code van je gast-wifi."), 14,
                      CLOCK_DIM, self.pt(400, 474), anchor="midbottom", max_w=self.px(760))

    def share_card(self, kop, lines, data, cx, top, size, text_y, max_w):
        """Een QR-code met eronder wat het is."""
        code = self.qr.get(data, self.px(size))
        self.s.blit(code, code.get_rect(midtop=self.pt(cx, top)))
        self.text(kop, 20, TEXT, self.pt(cx, text_y), anchor="center", bold=True, max_w=self.px(max_w))
        for n, line in enumerate(x for x in lines if x):
            self.text(line, 16, MUTED, self.pt(cx, text_y + 26 + n * 22), anchor="center", max_w=self.px(max_w))

    def draw_toast(self):
        with self.p.lock:
            msg, until = self.p.message, self.p.message_until
        if not msg or time.monotonic() > until:
            return
        f, pad = self.font(18, False), self.px(20)
        lines = self.wrap(msg, 18, self.px(self.L["toast_w"]) - 2 * pad)
        w = max(f.size(line)[0] for line in lines) + 2 * pad
        r = pygame.Rect(0, 0, w, len(lines) * f.get_linesize() + self.px(24))
        r.midbottom = self.pt(self.cx, self.L["toast_y"])
        pygame.draw.rect(self.s, TOAST, r, border_radius=min(r.h // 2, self.px(24)))
        self.paragraph(msg, 18, TEXT, r.center, r.w - 2 * pad)

    @staticmethod
    def device_info(d):
        parts = [tr(TYPES.get(d.get("type"), d.get("type", "")))]
        if d.get("volume_percent") is not None:
            parts.append(tr("volume {volume}%", volume=d["volume_percent"]))
        if d.get("is_restricted"):
            parts.append(tr("niet te bedienen via de API"))
        elif d.get("is_active"):
            parts.append(tr("speelt nu"))
        return " · ".join(parts)

    # -- acties --

    def back(self):
        self.view, self.scroll = "now", 0

    def open_devices(self):
        self.devices_asked = time.monotonic()
        self.p.load_devices()
        self.view, self.scroll = "devices", 0

    def open_playlists(self):
        self.p.load_playlists(keep=True)  # oude lijst blijft staan tot de nieuwe binnen is
        self.view, self.scroll = "playlists", 0

    def open_recent(self):
        self.p.load_recent()
        self.view, self.scroll = "recent", 0

    def pick_context(self, uri):
        if self.p.play_context(uri):
            self.back()
        else:
            self.open_devices()

    def open_queue(self):
        self.p.load_queue()
        self.view, self.scroll = "queue", 0

    def open_timer(self):
        self.view = "timer"

    def open_menu(self):
        self.view = "menu"

    def open_lyrics(self):
        self.view, self.scroll = "lyrics", 0

    def open_share(self):
        self.view, self.share_tab = "share", 0

    # toetsenbord

    def open_keyboard(self, title, text, label, on_done):
        self.kb = {"title": title, "text": text, "label": label, "on_done": on_done, "back": self.view}
        self.view = "keyboard"

    def kb_type(self, chars):
        if len(self.kb["text"]) < 60:
            self.kb["text"] += chars

    def kb_backspace(self):
        self.kb["text"] = self.kb["text"][:-1]

    def kb_cancel(self):
        self.view = self.kb["back"]

    def kb_done(self):
        self.view = self.kb["back"]
        self.kb["on_done"](self.kb["text"].strip())

    # zoeken

    def open_search(self):
        self.open_keyboard(tr("Nummer, artiest, album…"), self.search_query, tr("Zoek"), self.run_search)

    def run_search(self, query):
        if not query:
            return
        self.search_query = query
        self.p.search(query)
        self.view, self.scroll = "search", 0

    def pick_result(self, kind, item):
        if self.p.play_item(kind, item):
            self.back()
        else:
            self.open_devices()

    # instellingen

    def open_settings(self):
        self.view, self.scroll = "settings", 0

    def open_setting(self, page):
        self.view = page

    def apply_settings(self):
        s = self.settings
        set_language(s["taal"])
        if s["draaien"] != self.rotation:
            self.configure()
        self.fonts.clear()        # lettertype kan veranderd zijn
        self.text_cache.clear()
        self.idle_after = s["idle_min"] * 60 if s["idle_min"] else math.inf
        self.night = parse_night(s["nacht_van"], s["nacht_tot"]) if s["nacht_stijl"] != "uit" else None
        if self.weather:
            self.weather.set_place(s["weer_plaats"])

    def change_setting(self, key, value):
        self.settings[key] = value
        save_settings(self.settings)
        self.apply_settings()

    def edit_place(self):
        self.open_keyboard(tr("Plaats, bijv. Utrecht"), self.settings["weer_plaats"], tr("Opslaan"),
                           lambda place: self.change_setting("weer_plaats", place))

    def step_night(self, key, direction):
        h, m = (int(x) for x in self.settings[key].split(":"))
        minutes = (h * 60 + m + direction * NIGHT_STEP) % (24 * 60)
        self.change_setting(key, f"{minutes // 60:02d}:{minutes % 60:02d}")

    def pick_sleep(self, minutes):
        self.p.set_sleep(minutes)
        self.p.say(tr("Slaaptimer: de muziek stopt over {minutes} minuten", minutes=minutes) if minutes
                   else tr("Slaaptimer uit"))
        self.back()

    def pick_device(self, d):
        if d.get("is_restricted"):
            self.p.say(tr("Dit apparaat laat zich niet op afstand bedienen"))
            return
        self.p.transfer(d["id"])
        self.back()

    def pick_playlist(self, pl):
        self.playlist, self.playlist_scroll = pl, self.scroll
        if self.p.tracks_for != pl["id"]:
            self.p.load_tracks(pl["id"])
        self.view, self.scroll = "tracks", 0

    def back_to_playlists(self):
        self.view, self.scroll = "playlists", self.playlist_scroll

    def play_playlist(self):
        self.pick_track(None)

    def pick_track(self, position):
        # In de context van de playlist, zodat hij daarna gewoon doorspeelt.
        if self.p.play_context(self.playlist["uri"], position):
            self.back()
        else:
            self.open_devices()

    # -- aanraken en slepen --

    def on_down(self, pos):
        self.swallow = self.resting()  # eerste tik maakt alleen wakker
        self.last_touch = time.monotonic()
        self.press, self.dragging, self.drag = (pos, self.scroll), False, None
        if self.swallow:
            return
        for key, contains, to_frac, on_release, on_drag in self.sliders:
            if contains(pos):
                self.drag = [key, to_frac(pos), to_frac, on_release, on_drag]
                self.drag_sent = 0.0
                return

    def on_move(self, pos):
        self.last_touch = time.monotonic()
        if self.drag:
            self.drag[1] = self.drag[2](pos)
            on_drag = self.drag[4]
            if on_drag and time.monotonic() - self.drag_sent > 0.5:
                self.drag_sent = time.monotonic()
                on_drag(self.drag[1])
            return
        if not self.press or self.view in ("now", "menu", "timer", "keyboard",
                                              "set_weer", "set_rust", "set_nacht", "set_font", "set_taal",
                                              "set_kleur", "set_scherm", "info", "share"):
            return
        dy = pos[1] - self.press[0][1]
        if abs(dy) > self.px(12):
            self.dragging = True
        if self.dragging:
            self.scroll = max(0, self.press[1] - dy)

    def on_up(self, pos):
        if self.drag:
            _, _, to_frac, on_release, _ = self.drag
            self.drag = None
            on_release(to_frac(pos))
        elif self.press and not self.dragging and not self.swallow:
            for r, action in reversed(self.buttons):
                if r.collidepoint(pos):
                    action()
                    break
        self.press = None


def open_display(shape):
    """Het scherm openen. Geeft (canvas, framebuffer) terug; framebuffer is None tenzij plan B aan staat."""
    if os.environ.get("SPOTISCHERM_FRAMEBUFFER") == "1":
        # Plan B voor Pi's waar SDL via KMS geen beeld geeft: tekenen op een los canvas en dat zelf
        # naar de console kopiëren. Touch en muis lezen we dan ook zelf uit.
        from fbdev import FrameBuffer, InputReader
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.display.init()
        pygame.font.init()
        fb = FrameBuffer()
        pygame.display.set_mode((fb.w, fb.h))  # nodig voor pygame, maar we tekenen er niet op
        # Tekenen op een canvas in precies het formaat van het beeldgeheugen: dan is tonen
        # alleen kopiëren, zonder omzetten (scheelt op een Pi 1 zo'n 140 ms per beeld).
        canvas = pygame.Surface((fb.w, fb.h), 0, fb.bpp, fb.masks)
        InputReader(fb.w, fb.h).start()
        return canvas, fb
    if os.environ.get("SDL_VIDEODRIVER") == "kmsdrm":
        # Zonder dit kiest SDL desktop-OpenGL, die de Pi niet heeft: dan blijft het scherm
        # zwart zonder foutmelding. De Pi kan alleen OpenGL ES.
        os.environ.setdefault("SDL_RENDER_DRIVER", "opengles2")
    pygame.display.init()
    pygame.font.init()
    if os.environ.get("SPOTISCHERM_WINDOWED") == "1":
        surface = pygame.display.set_mode((540, 540) if shape == "rond" else (BASE_W, BASE_H))
    else:
        surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        # Op een touchscreen hoort geen cursor; met SPOTISCHERM_MUIS=1 kun je schermvullend met de muis werken.
        pygame.mouse.set_visible(os.environ.get("SPOTISCHERM_MUIS") == "1")
    pygame.display.set_caption("SpotiScherm")
    return surface, None


def quit_requested():
    for ev in pygame.event.get((pygame.QUIT, pygame.KEYDOWN)):
        if ev.type == pygame.QUIT or ev.key == pygame.K_ESCAPE:
            return True
    return False


def main():
    load_config()
    # config.env geeft de standaardwaarden; wat je op het scherm instelt, wint.
    night_from = os.environ.get("NACHT_VAN", "23:00").strip()
    night_to = os.environ.get("NACHT_TOT", "07:00").strip()
    settings = {
        "weer_plaats": os.environ.get("WEER_PLAATS", "").strip(),
        "idle_min": float(os.environ.get("SPOTISCHERM_IDLE_MIN", "5")),
        "nacht_stijl": (os.environ.get("NACHT_STIJL", "rood").strip().lower()
                        if parse_night(night_from, night_to) else "uit"),
        "nacht_van": night_from or "23:00",
        "nacht_tot": night_to or "07:00",
        "rust_scherm": os.environ.get("RUST_SCHERM", "hoes").strip().lower(),
        "taal": os.environ.get("TAAL", "nl").strip().lower(),
        "lettertype": os.environ.get("LETTERTYPE", "standaard").strip().lower(),
        "kleur": os.environ.get("KLEUR", "groen").strip().lower(),
        "draaien": int(os.environ.get("DRAAIEN", "0") or 0),
    }
    saved = load_settings()
    if "nacht_aan" in saved:  # oude instellingen: aan/uit werd "zwart"/"uit"
        saved.setdefault("nacht_stijl", "zwart" if saved["nacht_aan"] else "uit")
        del saved["nacht_aan"]
    settings.update(saved)
    if settings["nacht_stijl"] not in NIGHT_STYLES:
        settings["nacht_stijl"] = "rood"
    if settings["rust_scherm"] not in ("klok", "hoes"):
        settings["rust_scherm"] = "hoes"
    if settings["taal"] not in LANGUAGES:
        settings["taal"] = "nl"
    if settings["lettertype"] not in FONT_NAMES:
        settings["lettertype"] = "standaard"
    if settings["kleur"] not in ACCENT_COLORS:
        settings["kleur"] = "groen"
    if settings["draaien"] not in dict(ROTATIONS):
        settings["draaien"] = 0
    weather = Weather(settings["weer_plaats"], os.environ.get("WEER_LAND", "NL").strip())
    shape = os.environ.get("SCHERM_VORM", "auto").strip().lower()
    surface, framebuffer = open_display(shape)
    w, h = surface.get_size()
    # auto: een (bijna) vierkant scherm is in de praktijk een rond scherm
    round_screen = shape == "rond" or (shape == "auto" and abs(w - h) <= 0.05 * max(w, h))
    economy = os.environ.get("SPOTISCHERM_ZUINIG") == "1"
    ui = Screen(surface, settings, weather, round_screen,
                preview=os.environ.get("SPOTISCHERM_WINDOWED") == "1", local=LocalDevices(), economy=economy,
                framebuffer=framebuffer)

    while not CACHE_PATH.exists():
        ui.draw_message(tr("Nog niet ingelogd bij Spotify"),
                        [tr("Log in via SSH op de Pi:"), "cd ~/spotify-scherm && .venv/bin/python app/auth.py"])
        if quit_requested():
            return
        time.sleep(1)

    ui.p = Player(small_art=economy)
    touch_fps, calm_fps = ECONOMY_FPS if economy else (FPS, CALM_FPS)
    clock = pygame.time.Clock()
    finger = None
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ui.view == "keyboard" and ev.type in (pygame.TEXTINPUT, pygame.KEYDOWN):
                # Een echt toetsenbord werkt ook (handig bij testen op de pc).
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
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return
            # Zonder desktop geeft SDL een touchscreen door als vinger (0..1); met desktop
            # komt er ook een nagebootste muisklik bij (touch=True), die slaan we dan over.
            if ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                if finger not in (None, ev.finger_id):
                    continue  # alleen de eerste vinger telt
                dw, dh = surface.get_size()
                pos = ui.map_touch((int(ev.x * (dw - 1)), int(ev.y * (dh - 1))))
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
                ui.on_down(ui.map_touch(ev.pos))
            elif ev.type == pygame.MOUSEMOTION and ev.buttons[0]:
                ui.on_move(ui.map_touch(ev.pos))
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                ui.on_up(ui.map_touch(ev.pos))
            elif ev.type == pygame.MOUSEWHEEL:
                ui.scroll = max(0, ui.scroll - ev.y * ui.px(60))
        started = time.perf_counter()
        ui.draw()
        ui.frame_ms = ui.frame_ms * 0.9 + (time.perf_counter() - started) * 100  # gemiddelde in ms
        ui.fps = clock.get_fps()
        # Alleen snel tekenen als iemand het scherm aanraakt: scheelt veel CPU op de Pi,
        # zeker bij een groot scherm zoals 1080x1080.
        if ui.drag or time.monotonic() - ui.last_touch < 3:
            clock.tick(touch_fps)
        elif ui.animating:
            clock.tick(MARQUEE_FPS)
        else:
            clock.tick(2 if ui.resting() else calm_fps)


if __name__ == "__main__":
    main()
