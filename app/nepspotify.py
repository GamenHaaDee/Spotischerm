"""Een nep-Spotify: doet alsof het de Spotify Web API is, met verzonnen muziek.

Voor de tests, de browserdemo en om de app op de pc te proberen zonder Spotify-account en zonder
quotum te verbruiken (SPOTISCHERM_NEP_SPOTIFY=1 in config.env). Er gaat niets het internet op.
Alleen de functies die SpotiScherm gebruikt; ze geven terug wat Spotify ook zou geven.
"""
import random
import time

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
TRACKS, ALBUM_TRACKS = {}, {}  # nummer-id -> (naam, ms, artiest, album); album-id -> [nummer-ids]
for _album_id, (_name, _artist, _year, _kind, _songs) in ALBUMS.items():
    ALBUM_TRACKS[_album_id] = []
    for _n, (_song, _seconds) in enumerate(_songs):
        ALBUM_TRACKS[_album_id].append(f"{_album_id}t{_n}")
        TRACKS[f"{_album_id}t{_n}"] = (_song, _seconds * 1000, _artist, _album_id)
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


def lyrics_for(item):
    """Bij elk nummer dezelfde verzonnen tekst, verdeeld over de lengte van het nummer: [(seconden, regel)]."""
    seconds = (item.get("duration_ms") or 200000) / 1000
    step = (seconds - 20) / len(LYRICS_LINES)
    return [(12 + i * step, line) for i, line in enumerate(LYRICS_LINES)]


class FakeSpotify:
    """De Spotify Web API, met de verzonnen muziek hierboven.

    image_prefix: begin van de adressen van de hoezen (bijv. "demo://hoes/"); None = geen hoezen.
    """

    def __init__(self, image_prefix=None, playing=True):
        self.image_prefix = image_prefix
        self.devices_list = [
            {"id": "d1", "name": "Woonkamer Speaker", "type": "Speaker", "volume_percent": 45},
            {"id": "d2", "name": "Keuken", "type": "Speaker", "volume_percent": 30},
            {"id": "d3", "name": "Tv Woonkamer", "type": "TV", "volume_percent": 20},
            {"id": "d4", "name": "Pixel-telefoon", "type": "Smartphone", "volume_percent": 80},
        ]
        self.device = "d1"
        # gelikete nummers, nieuwste eerst (een dict houdt de volgorde vast)
        self.liked = dict.fromkeys(f"spotify:track:{t}" for t in ("b1t0", "b3t0", "b5t1", "b2t2", "b4t0"))
        self.queue_extra = []
        self.recent = []
        self.shuffle_state, self.repeat_state = False, "off"
        self._play("spotify:playlist:p1", PLAYLISTS["p1"][1], 0, playing=playing, progress=44000)

    # -- muziek als Spotify-objecten --

    def _artist(self, artist_id):
        return {"id": artist_id, "uri": f"spotify:artist:{artist_id}", "name": ARTISTS[artist_id], "type": "artist"}

    def _album(self, album_id):
        name, artist_id, year, kind, _ = ALBUMS[album_id]
        album = {"id": album_id, "uri": f"spotify:album:{album_id}", "name": name, "album_type": kind,
                 "release_date": f"{year}-05-01", "artists": [self._artist(artist_id)], "images": []}
        if self.image_prefix:
            album["images"] = [{"url": f"{self.image_prefix}{album_id}.jpg", "width": 300, "height": 300}]
        return album

    def _track(self, track_id):
        name, ms, artist_id, album_id = TRACKS[track_id]
        return {"id": track_id, "uri": f"spotify:track:{track_id}", "type": "track", "name": name, "duration_ms": ms,
                "artists": [self._artist(artist_id)], "album": self._album(album_id)}

    def _playlist(self, playlist_id):
        name, tracks = PLAYLISTS[playlist_id]
        return {"id": playlist_id, "uri": f"spotify:playlist:{playlist_id}", "name": name,
                "owner": {"display_name": "Demo"}, "tracks": {"total": len(tracks)}}

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

    def _active_device(self):
        d = next(d for d in self.devices_list if d["id"] == self.device)
        return dict(d, is_active=True)

    def current_playback(self, additional_types=None):
        pos = self._position()
        return {"is_playing": self.playing, "progress_ms": int(pos), "item": self._track(self.order[self.index]),
                "device": self._active_device(), "shuffle_state": self.shuffle_state,
                "repeat_state": self.repeat_state,
                "context": ({"uri": self.context_uri, "type": self.context_uri.split(":")[1]}
                            if self.context_uri else None)}  # losse nummers (zoals likes): geen context

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
        elif uris and len(uris) > 1:  # een lijst losse nummers, zoals je likes
            self._play(None, [u.split(":")[-1] for u in uris], (offset or {}).get("position", 0))
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
        self.liked = {**dict.fromkeys(uris), **self.liked}  # nieuwste vooraan

    def current_user_saved_tracks_delete(self, uris):
        for uri in uris:
            self.liked.pop(uri, None)

    def current_user_saved_tracks(self, limit=20, offset=0):
        uris = list(self.liked)
        page = uris[offset:offset + limit]
        return {"items": [{"track": self._track(u.split(":")[-1])} for u in page], "total": len(uris),
                "offset": offset, "next": "volgende" if offset + limit < len(uris) else None}

    def current_user_playlists(self, limit=50):
        return {"items": [self._playlist(p) for p in PLAYLISTS], "next": None}

    def playlist_items(self, playlist_id, limit=100, additional_types=None):
        ids = PLAYLISTS[playlist_id.split(":")[-1]][1]
        return {"items": [{"track": self._track(t)} for t in ids], "offset": 0, "next": None}

    def playlist(self, uri, fields=None):
        return self._playlist(uri.split(":")[-1])

    def album(self, album_id):
        album = self._album(album_id.split(":")[-1])
        album["tracks"] = {"items": [self._track(t) for t in ALBUM_TRACKS[album["id"]]], "next": None}
        return album

    def artist(self, artist_id):
        return self._artist(artist_id.split(":")[-1])

    def artist_albums(self, artist_id, album_type=None, limit=10):
        return {"items": [self._album(a) for a, v in ALBUMS.items() if v[1] == artist_id], "next": None}

    def next(self, page):
        return None

    def search(self, q, limit=10, type="track"):
        q = q.lower().replace('artist:"', "").replace('"', "").strip()

        def match(name):
            return not q or q in name.lower()

        tracks = [self._track(t) for t, v in TRACKS.items() if match(v[0]) or match(ARTISTS[v[2]])]
        out = {"tracks": {"items": (tracks or [self._track(t) for t in TRACKS])[:limit]}}
        if "artist" in type:
            out["artists"] = {"items": [self._artist(a) for a, n in ARTISTS.items() if match(n)]}
            out["albums"] = {"items": [self._album(a) for a, v in ALBUMS.items()
                                       if match(v[0]) or match(ARTISTS[v[1]])]}
            out["playlists"] = {"items": [self._playlist(p) for p, v in PLAYLISTS.items() if match(v[0])]}
        return out

    def queue(self):
        upcoming = self.queue_extra + self.order[self.index + 1:]
        return {"queue": [self._track(t) for t in upcoming[:20]]}

    def add_to_queue(self, uri, device_id=None):
        self.queue_extra.append(uri.split(":")[-1])

    def current_user_recently_played(self, limit=50):
        def stamp(t):
            return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(t))

        items = [{"track": self._track(t), "played_at": stamp(when),
                  "context": {"uri": "spotify:playlist:p1"}} for t, when in self.recent[:limit]]
        older = [("b3t1", 3), ("b2t0", 26), ("b5t2", 50)]
        items += [{"track": self._track(t), "played_at": stamp(time.time() - h * 3600),
                   "context": {"uri": "spotify:album:" + t[:2]}} for t, h in older]
        return {"items": items}

    def current_user_top_artists(self, limit=20, offset=0, time_range="medium_term"):
        order = {"short_term": ["a2", "a1", "a3"], "medium_term": ["a1", "a2", "a3"], "long_term": ["a1", "a3"]}
        return {"items": [self._artist(a) for a in order[time_range]][:limit], "total": len(order[time_range])}

    def current_user_top_tracks(self, limit=20, offset=0, time_range="medium_term"):
        ids = list(TRACKS)[: {"short_term": 6, "medium_term": 12, "long_term": 16}[time_range]]
        return {"items": [self._track(t) for t in ids][:limit], "total": len(ids)}

    def current_user(self):
        return {"id": "demo", "display_name": "Demo"}
