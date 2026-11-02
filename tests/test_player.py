"""De Player tegen de nep-Spotify: bedienen, liken, zoeken, wachtrij en hoe vaak hij Spotify vraagt."""
import time

import pytest

import spotischerm as app
from conftest import sync
from nepspotify import PLAYLISTS, TRACKS, FakeSpotify


@pytest.fixture
def player():
    p = app.Player(sp=FakeSpotify(), threads=False)
    p._refresh()
    return p


def now_playing(player):
    pb, _ = player.snapshot()
    return pb["item"]["name"], pb["is_playing"]


def test_starts_with_the_first_song(player):
    assert now_playing(player) == ("Neon Horizon", True)


def test_pause_shows_immediately_and_sticks(player):
    player.toggle()
    assert now_playing(player)[1] is False  # meteen, nog voor Spotify antwoordt
    sync(player)
    assert now_playing(player)[1] is False
    player.toggle()
    sync(player)
    assert now_playing(player)[1] is True


def test_next_and_previous(player):
    player.next()
    sync(player)
    assert now_playing(player)[0] == TRACKS[PLAYLISTS["p1"][1][1]][0]
    player.previous()  # nog geen 3 seconden in het nummer: terug naar het vorige
    sync(player)
    assert now_playing(player)[0] == "Neon Horizon"


def test_previous_after_three_seconds_restarts_the_song(player):
    player.previous()  # de nep-Spotify begint op 0:44
    sync(player)
    pb, _ = player.snapshot()
    assert pb["item"]["name"] == "Neon Horizon" and pb["progress_ms"] < 3000


def test_like_and_unlike(player):
    uri = "spotify:track:b1t0"
    assert player.liked_state(uri) is None  # nog niet gevraagd
    player.work()
    assert player.liked_state(uri) is True
    player.toggle_like(uri)
    assert player.liked_state(uri) is False
    player.work()
    assert uri not in player.sp.liked


def test_volume_knob_sends_only_the_last_value(player):
    for _ in range(5):
        player.nudge_volume(3)
    assert player.snapshot()[0]["device"]["volume_percent"] == 60
    player.flush_volume()
    player.work()
    assert player.sp.devices_list[0]["volume_percent"] == 60
    player.flush_volume()  # niets meer te sturen
    assert player.work() is False


def test_search(player):
    player.search("arcade")
    player.work()
    kinds = {(kind, item["name"]) for kind, item in player.search_results}
    assert ("track", "Arcade Heart") in kinds


def test_play_a_playlist_from_a_position(player):
    assert player.play_context("spotify:playlist:p2", position=1)
    sync(player)
    assert now_playing(player)[0] == TRACKS[PLAYLISTS["p2"][1][1]][0]


def test_queue_and_devices(player):
    pb, _ = player.snapshot()
    player.add_to_queue({"uri": "spotify:track:b5t1", "name": "Fietsen naar huis"})
    player.load_queue()
    player.work()
    assert player.queue_items[0]["name"] == "Fietsen naar huis"
    player.load_devices()
    player.work()
    assert len(player.devices) == 4
    player.transfer("d2")
    sync(player)
    assert player.snapshot()[0]["device"]["name"] == "Keuken"


def test_playlists_tracks_artist_and_album(player):
    player.load_playlists()
    player.load_tracks("p3")
    player.load_artist("a1")
    player.load_album("b3")
    player.work()
    assert [p["name"] for p in player.playlists][0] == "Avondrit"
    assert len(player.tracks) == len(PLAYLISTS["p3"][1])
    assert player.artist_page["artist"]["name"] == "The Example Band"
    assert len(player.album_page["all_tracks"]) == 4


# -- hoe vaak de app Spotify vraagt (zie BUG-QUOTA: het quotum is op te maken) --

def interval(pace, playing, quiet_minutes=0, until_end=None):
    p = app.Player(sp=FakeSpotify(), threads=False)
    item = {"duration_ms": 200000}
    progress = 200000 - until_end * 1000 if until_end is not None else 10000
    p.playback = {"is_playing": True, "progress_ms": progress, "item": item} if playing else None
    p.fetched_at = time.monotonic()
    p.pace = pace
    p.last_playing = time.monotonic() - quiet_minutes * 60
    return p.poll_interval()


def test_poll_interval_depends_on_use():
    assert interval("actief", playing=True) == app.POLL_SECONDS
    assert interval("actief", playing=False, quiet_minutes=120) == app.POLL_PAUSED  # in gebruik: geen diepe slaap
    assert interval("rust", playing=True) == app.POLL_REST[0]
    assert interval("rust", playing=False, quiet_minutes=10) == app.POLL_REST[1]
    assert interval("slaap", playing=False, quiet_minutes=10) == app.POLL_SLEEP


def test_deep_sleep_after_half_an_hour_of_silence():
    assert interval("rust", playing=False, quiet_minutes=31) == app.POLL_DEEP
    assert interval("slaap", playing=False, quiet_minutes=31) == app.POLL_DEEP


def test_asks_again_right_after_the_song_ends():
    assert interval("rust", playing=True, until_end=4) == pytest.approx(5, abs=0.5)


def test_becoming_active_wakes_the_poller(player):
    player.set_pace("slaap")
    player._wake.clear()
    player.set_pace("rust")  # iemand komt de kamer in
    assert player._wake.is_set()
    player._wake.clear()
    player.set_pace("slaap")
    assert not player._wake.is_set()


# -- gelikete nummers --

def test_liked_songs_list_and_play(player):
    player.load_tracks(app.LIKED_ID)
    player.work()
    names = [item["name"] for _, item in player.tracks]
    assert player.liked_total == 5 and names[0] == "Neon Horizon"
    uris = [item["uri"] for _, item in player.tracks]
    assert player.play_tracks(uris, 2)
    sync(player)
    pb, _ = player.snapshot()
    assert pb["item"]["name"] == names[2] and pb["context"] is None  # losse nummers: geen context


def test_a_new_like_comes_first(player):
    player.toggle_like("spotify:track:b3t3")
    player.load_tracks(app.LIKED_ID)
    player.work()
    assert player.tracks[0][1]["name"] == "Game Over (Not Yet)"


def test_play_tracks_sends_at_most_100(player, monkeypatch):
    sent = []
    monkeypatch.setattr(player, "_run", lambda fn, *args: sent.append(args))
    uris = [f"spotify:track:{n:022d}" for n in range(250)]
    player.play_tracks(uris, 120)
    _, _, sent_uris, offset = sent[0]
    assert len(sent_uris) == 100 and sent_uris[0] == uris[120] and offset == {"position": 0}


# -- jouw top --

def test_top_is_fetched_once_and_kept(player):
    player.load_top("artists", "short_term")
    assert player.top_items("artists", "short_term") is None  # aan het laden
    player.work()
    assert [a["name"] for a in player.top_items("artists", "short_term")][0] == "Pixel Parade"
    player.load_top("artists", "short_term")  # nog vers: geen nieuw verzoek
    assert player.work() is False
    player.load_top("tracks", "long_term")
    player.work()
    assert len(player.top_items("tracks", "long_term")) == 16


def test_likes_work_right_after_a_reboot(player, monkeypatch):
    """monotonic() telt vanaf het opstarten; vlak na een herstart is dat nog klein (GitHub vond dit)."""
    monkeypatch.setattr(app.time, "monotonic", lambda: 12.0)
    uri = "spotify:track:b1t0"
    assert player.liked_state(uri) is None
    player.work()
    assert player.liked_state(uri) is True
