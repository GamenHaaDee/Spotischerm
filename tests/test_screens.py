"""Elk scherm tekenen, in elke schermvorm en elke taal: vangt fouten die je anders pas op de Pi ziet."""
import time

import pygame
import pytest

import common
import spotischerm as app
from conftest import FakeWeather, settings, sync
from i18n import LANGUAGES
from lyrics import Lyrics
from nepspotify import FakeSpotify, lyrics_for

SHAPES = {"rechthoek": ((800, 480), False), "rond": ((480, 480), True), "staand": ((480, 800), False)}
VIEWS = ["now", "devices", "playlists", "queue", "timer", "menu", "search", "settings", "recent", "set_weer",
         "set_rust", "set_nacht", "set_font", "set_taal", "set_kleur", "set_scherm", "info", "set_power", "set_web",
         "set_update", "lyrics", "share"]


def make_screen(shape="rechthoek", lang="nl", **changes):
    size, round_screen = SHAPES[shape]
    ui = app.Screen(pygame.display.set_mode(size), settings(taal=lang, **changes), FakeWeather(), round_screen)
    ui.p = app.Player(sp=FakeSpotify(), threads=False)
    ui.lyrics.get = lambda item: Lyrics(synced=lyrics_for(item))
    ui.booting = False
    sync(ui.p)
    return ui


@pytest.mark.parametrize("lang", list(LANGUAGES))
@pytest.mark.parametrize("shape", list(SHAPES))
def test_every_view_draws(shape, lang):
    ui = make_screen(shape, lang)
    ui.p.load_devices()
    ui.p.load_playlists()
    ui.p.load_queue()
    ui.p.load_recent()
    ui.p.search("night")
    ui.p.work()
    for view in VIEWS:
        ui.view = view
        ui.draw()
    # pagina's die eerst iets laden
    ui.pick_playlist(ui.p.playlists[0])
    ui.p.work()
    ui.draw()
    ui.open_artist("a1", "The Example Band")
    ui.p.work()
    ui.draw()
    ui.open_album("b1", "Night Drive")
    ui.p.work()
    ui.draw()
    ui.open_keyboard("Zoeken", "neon", "Zoek", lambda text: None)
    ui.draw()


@pytest.mark.parametrize("shape", list(SHAPES))
def test_tour_draws_every_step(shape):
    ui = make_screen(shape)
    ui.start_tour()
    for _ in range(len(ui.tour_steps())):
        ui.draw()
        ui.tour_go(1)
    assert ui.view == "now"  # na de laatste stap klaar
    assert ui.settings["rondleiding_gezien"]


def test_special_states_draw():
    ui = make_screen()
    ui.booting = True  # opstartscherm
    ui.draw()
    ui.booting = False
    ui.start_cleaning()  # schoonmaakstand
    ui.draw()
    ui.clean_until = 0
    ui.overlay = ("volume", 42, time.monotonic() + 5)  # volumebalk van de knop
    ui.draw()
    ui.last_touch = time.monotonic() - 3600  # rustscherm
    ui.draw()
    common._blocked_until = time.time() + 600  # Spotify laat ons wachten: rode balk
    ui.draw()
    common._blocked_until = 0.0


def test_swipe_left_plays_the_next_song():
    ui = make_screen()
    ui.draw()
    ui.on_down((600, 300))
    ui.on_move((400, 300))
    ui.on_up((400, 300))
    sync(ui.p)
    assert ui.p.snapshot()[0]["item"]["name"] != "Neon Horizon"


def test_info_page_shows_the_request_counter():
    ui = make_screen()
    for _ in range(7):
        common.counter.add()
    labels = dict(ui.system_info())
    assert labels["Verzoeken dit uur"] == "7"
    assert labels["Verzoeken vandaag"].startswith("7 ")


def test_settings_change_language_and_rotation():
    ui = make_screen()
    ui.change_setting("taal", "de")
    ui.view = "settings"
    ui.draw()
    ui.change_setting("draaien", 90)  # staand: canvas wordt gedraaid
    assert ui.shape == "staand"
    ui.draw()


class Login:
    """Stand-in voor login.PhoneLogin, zonder Spotify."""

    def __init__(self, minutes=0):
        self.minutes = minutes

    def open(self):
        self.minutes = 10

    def minutes_left(self):
        return self.minutes


@pytest.mark.parametrize("shape", list(SHAPES))
def test_login_screens_draw(shape):
    ui = make_screen(shape)
    ui.web_port = 8080
    ui.web_url = lambda: "http://192.168.1.50:8080"
    ui.login = Login()
    ui.draw_login_wait()  # nog niet ingelogd: QR-code naar /inloggen
    ui.open_account()
    ui.p.work()
    ui.draw()
    assert ui.account_name() == "Demo"
    ui.relogin()  # Opnieuw inloggen: QR-code met aftellen
    ui.draw()
    ui.login = None  # zonder telefoonpagina: uitleg via SSH
    ui.draw()
    ui.draw_login_wait()


@pytest.mark.parametrize("shape", list(SHAPES))
def test_update_page_with_a_previous_version(shape, monkeypatch):
    ui = make_screen(shape)
    monkeypatch.setattr(app, "previous", lambda: {"versie": "1.3", "nieuw": [], "op": 0})
    restored = []
    monkeypatch.setattr(app, "restore", lambda: restored.append(True) or "1.3")
    monkeypatch.setattr(app.subprocess, "run", lambda *a, **kw: None)  # niet echt herstarten
    ui.open_setting("set_update")
    ui.draw()
    assert ui.previous_version["versie"] == "1.3"
    ui.update_confirm = "terug"  # Vorige versie terugzetten → bevestigen
    ui.draw()
    ui.run_restore()
    assert restored and ui.previous_version is None


def test_liked_songs_on_top_of_playlists():
    ui = make_screen()
    ui.p.load_playlists()
    ui.p.work()
    ui.open_playlists()
    ui.p.work()
    ui.draw()
    ui.pick_playlist(ui.liked_playlist())
    ui.p.work()
    ui.draw()
    assert ui.view == "tracks" and len(ui.p.tracks) == 5
    ui.pick_track(1)  # vanaf het tweede gelikete nummer
    sync(ui.p)
    assert ui.p.snapshot()[0]["item"]["uri"] == ui.p.tracks[1][1]["uri"]


@pytest.mark.parametrize("shape", list(SHAPES))
def test_your_top_page(shape):
    ui = make_screen(shape)
    ui.view = "playlists"
    ui.open_top()
    ui.p.work()
    ui.draw()
    ui.switch_top_period()  # laatste 6 maanden
    ui.switch_top_kind()  # nummers
    ui.p.work()
    ui.draw()
    assert ui.top_kind == "tracks" and ui.p.top_items("tracks", "medium_term")
    ui.p.can_top = False  # oude login zonder toestemming: uitleg
    ui.draw()


@pytest.mark.parametrize("style", ["digitaal", "analoog", "flip"])
@pytest.mark.parametrize("shape", list(SHAPES))
def test_clock_styles(shape, style):
    ui = make_screen(shape, klok_stijl=style, rust_scherm="klok")
    ui.last_touch = time.monotonic() - 3600  # rustscherm: de klok
    ui.draw()
    if style == "flip":  # midden in het omklappen, in beide helften van de animatie
        for moment in (0.2, 0.45):
            ui.flip_shown = {i: (v, "00", time.monotonic() - moment) for i, (v, _, _) in ui.flip_shown.items()}
            ui.draw()
            assert ui.animating
    ui.view = "set_rust"
    ui.last_touch = time.monotonic()
    ui.draw()
