"""Gedeelde opzet voor de tests: zonder scherm, zonder Spotify, en zonder je eigen bestanden aan te raken.

Draaien: python -m pytest   (nodig: pytest, pygame, requests, spotipy, segno)
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # geen echt scherm nodig
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import pygame  # noqa: E402
import pytest  # noqa: E402

import common  # noqa: E402
import spotischerm  # noqa: E402

pygame.display.init()
pygame.font.init()


@pytest.fixture(autouse=True)
def eigen_bestanden(tmp_path, monkeypatch):
    """Wachttijd, teller en instellingen in een tijdelijke map, nooit in die van de app."""
    monkeypatch.setattr(common, "WAIT_PATH", tmp_path / ".spotify-wachten")
    monkeypatch.setattr(common, "_blocked_until", 0.0)
    counter = common.RequestCounter(tmp_path / ".spotify-teller")
    monkeypatch.setattr(common, "counter", counter)
    monkeypatch.setattr(spotischerm, "counter", counter)
    monkeypatch.setattr(spotischerm, "save_settings", lambda settings: None)
    yield tmp_path


def settings(**changes):
    """Standaardinstellingen zoals main() ze opbouwt, met eventueel wat anders."""
    base = {"weer_plaats": "Utrecht", "idle_min": 5, "nacht_stijl": "uit", "nacht_van": "23:00",
            "nacht_tot": "07:00", "rust_scherm": "hoes", "taal": "nl", "lettertype": "standaard",
            "kleur": "groen", "draaien": 0, "rondleiding_gezien": True}
    base.update(changes)
    return base


class FakeWeather:
    error = None
    summary = "18° · Half bewolkt · max 22° min 14°"
    rain = "Droog de komende uren"

    def set_place(self, place):
        pass


def sync(player):
    """Wat de achtergrondthreads van de app doen: klussen uitvoeren en de nieuwe stand ophalen."""
    player.work()
    player._hold_until = 0.0
    player._refresh()
