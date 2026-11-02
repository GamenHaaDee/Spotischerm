"""Inloggen via je telefoon: het geplakte adres lezen, en wanneer het wel en niet mag."""
import pytest

import login as login_module
from login import PhoneLogin, code_from


@pytest.mark.parametrize("pasted, expected", [
    ("http://127.0.0.1:8888/callback?code=AQB123&state=abc", ("AQB123", "abc")),
    ("  http://127.0.0.1:8888/callback?code=AQB123  ", ("AQB123", None)),
    ("AQB123", ("AQB123", None)),  # alleen de code
    ("http://127.0.0.1:8888/callback?error=access_denied", (None, None)),  # 'Annuleren' gekozen
    ("hallo daar", (None, None)),
    ("", (None, None)),
])
def test_code_from(pasted, expected):
    assert code_from(pasted) == expected


class FakeOAuth:
    """Doet alsof Spotify de code omzet in een login: schrijft het cachebestand."""

    def __init__(self, cache, accept=True):
        self.cache, self.accept = cache, accept

    def get_authorize_url(self):
        return "https://accounts.spotify.com/authorize?state=test"

    def get_access_token(self, code, as_dict=False, check_cache=False):
        if not self.accept:
            raise login_module.SpotifyOauthError("invalid_grant")
        self.cache.write_text('{"access_token": "nep"}')
        return "nep"


@pytest.fixture
def phone(tmp_path, monkeypatch):
    cache = tmp_path / ".spotify-cache"
    login = PhoneLogin(cache_path=cache)
    login.fake = FakeOAuth(cache)
    monkeypatch.setattr(login, "_oauth", lambda: login.fake)
    return login


def test_first_login_works(phone):
    assert phone.allowed()
    phone.url()  # de link van deze poging (maakt de state)
    ok, _ = phone.finish(f"http://127.0.0.1:8888/callback?code=AQB&state={phone.state}")
    assert ok and phone.done and phone.cache_path.exists()


def test_only_this_attempt_counts(phone):
    phone.url()
    ok, _ = phone.finish("http://127.0.0.1:8888/callback?code=AQB&state=van-iemand-anders")
    assert not ok and not phone.cache_path.exists()


def test_without_a_link_from_the_pi_nothing_happens(phone):
    ok, _ = phone.finish("AQB")  # geen inlogpoging begonnen
    assert not ok


def test_refused_code(phone):
    phone.url()
    phone.fake.accept = False
    ok, message = phone.finish("AQB")
    assert not ok and "Spotify" in message


def test_logged_in_means_closed_until_opened_on_the_screen(phone):
    phone.cache_path.write_text("{}")
    assert not phone.allowed()
    assert phone.finish("AQB")[0] is False
    phone.open()  # op het scherm: Opnieuw inloggen
    assert phone.allowed() and phone.minutes_left() == 10
    phone.url()
    assert phone.finish(f"x?code=AQB&state={phone.state}")[0]
    assert not phone.allowed()  # na gelukt weer dicht
