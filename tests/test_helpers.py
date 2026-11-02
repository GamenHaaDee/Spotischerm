"""Kleine hulpfuncties: songteksten, versies, deellinks, wifi-QR en de GPIO-pinnen."""
import pytest

import hardware
from lyrics import Lyrics, clean_title, parse_lrc
from share import spotify_link, wifi_payload
from updates import version_tuple


def test_parse_lrc_with_empty_lines():
    lines = parse_lrc("[00:12.50]Eerste regel\n[00:15.00]\n[00:20.00][00:40.00]Refrein")
    assert lines == [(12.5, "Eerste regel"), (15.0, "♪"), (20.0, "Refrein"), (40.0, "Refrein")]
    assert Lyrics(synced=lines).index_at(21) == 2
    assert Lyrics(synced=lines).index_at(5) == -1


def test_clean_title():
    assert clean_title("Song - Remastered 2011") == "Song"
    assert clean_title("Song (feat. Iemand)") == "Song"


def test_version_order():
    assert version_tuple("v1.10") > version_tuple("1.9")
    assert version_tuple("1.3") == (1, 3)
    assert version_tuple("nieuw") == ()


def test_spotify_link():
    assert spotify_link("spotify:playlist:abc") == "https://open.spotify.com/playlist/abc"
    assert spotify_link("spotify:user:x:collection") is None
    assert spotify_link(None) is None


def test_wifi_payload_escapes_special_characters():
    assert wifi_payload("Thuis;Gast", "a:b") == "WIFI:T:WPA;S:Thuis\\;Gast;P:a\\:b;;"
    assert wifi_payload("Open", "", "geen") == "WIFI:T:nopass;S:Open;;"


@pytest.mark.parametrize("value, expected", [("", None), ("0", None), ("1", (5, 6, 26)), ("17,27,22", (17, 27, 22)),
                                             ("17,27", None), ("abc", None)])
def test_knob_pins(monkeypatch, value, expected):
    monkeypatch.setenv("SPOTISCHERM_DRAAIKNOP", value)
    assert hardware._pins("SPOTISCHERM_DRAAIKNOP", hardware.KNOB_PINS) == expected
