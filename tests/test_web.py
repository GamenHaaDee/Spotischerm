"""De telefoonpagina: instellingen, schermafdruk en verzoekjes van gasten."""
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pygame
import pytest

from web import REQUEST_MAX, SettingsServer

FIELDS = [{"key": "idle_min", "type": "choice", "label": "Rustscherm", "options": [(1, "1 min"), (5, "5 min")]}]


class Guests:
    def __init__(self):
        self.added = []

    def search(self, query):
        return [{"uri": "spotify:track:" + "a" * 22, "name": "Neon Horizon", "artist": "The Example Band",
                 "image": ""}]

    def add(self, uri, name):
        self.added.append(uri)
        return True, ""

    def now(self):
        return "Neon Horizon · The Example Band"


@pytest.fixture
def server():
    with socket.socket() as s:  # een vrije poort
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    settings = {"idle_min": 5}
    guests = Guests()
    srv = SettingsServer(port, lambda: (FIELDS, settings, "#1ed760"),
                         lambda key, value: int(value) if value in ("1", "5") else None, guests)
    srv.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):  # wachten tot hij luistert
        try:
            urllib.request.urlopen(url, timeout=1).read()
            break
        except OSError:
            time.sleep(0.05)
    srv.url, srv.guests_stub = url, guests
    return srv


def post(url, data, origin=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    if origin:
        req.add_header("Origin", origin)
    return urllib.request.urlopen(req, timeout=5)


def test_settings_page_and_change(server):
    page = urllib.request.urlopen(server.url, timeout=5).read().decode()
    assert "SpotiScherm" in page and "idle_min" in page

    def answer():  # het scherm verwerkt de wijziging, zoals de hoofdlus
        key, value = server.changes.get(timeout=5)
        answer.got = (key, value)
        server.changes.task_done()

    worker = threading.Thread(target=answer)
    worker.start()
    post(server.url + "/", {"idle_min": "1"})
    worker.join(5)
    assert answer.got == ("idle_min", 1)


def test_invalid_value_and_foreign_site_are_refused(server):
    page = post(server.url + "/", {"idle_min": "99"}).read().decode()
    assert "err" in page and server.changes.empty()
    with pytest.raises(urllib.error.HTTPError) as err:
        post(server.url + "/", {"idle_min": "1"}, origin="http://evil.example")
    assert err.value.code == 403


def test_screenshot(server):
    surface = pygame.Surface((80, 48))
    surface.fill((30, 215, 96))

    def screen_loop():  # wat de hoofdlus doet bij elk beeld
        for _ in range(100):
            server.take_shot(surface, lambda s: b"PNG-van-het-scherm")
            time.sleep(0.02)

    threading.Thread(target=screen_loop, daemon=True).start()
    reply = urllib.request.urlopen(server.url + "/scherm.png", timeout=5)
    assert reply.headers["Content-Type"] == "image/png"
    assert reply.read() == b"PNG-van-het-scherm"
    assert server.shot is None  # niets bewaard


def test_guest_requests_are_limited(server):
    uri = "spotify:track:" + "a" * 22
    page = urllib.request.urlopen(server.url + "/verzoekjes?q=neon", timeout=5).read().decode()
    assert "Neon Horizon" in page
    for _ in range(REQUEST_MAX):
        post(server.url + "/verzoekjes", {"uri": uri, "name": "Neon Horizon", "q": "neon"})
    page = post(server.url + "/verzoekjes", {"uri": uri, "name": "Neon Horizon", "q": "neon"}).read().decode()
    assert len(server.guests_stub.added) == REQUEST_MAX  # de vierde niet
    assert "err" in page
    with pytest.raises(urllib.error.HTTPError) as err:
        post(server.url + "/verzoekjes", {"uri": "spotify:track:x", "name": "x"})
    assert err.value.code == 400


class Login:
    """Stand-in voor login.PhoneLogin."""

    def __init__(self):
        self.open, self.pasted = True, []

    def allowed(self):
        return self.open

    def url(self):
        return "https://accounts.spotify.com/authorize?state=test"

    def finish(self, pasted):
        self.pasted.append(pasted)
        return "code=" in pasted, "Gelukt!" if "code=" in pasted else "Daar staat geen code in."


def test_login_page(server):
    server.login = Login()
    page = urllib.request.urlopen(server.url + "/inloggen", timeout=5).read().decode()
    assert "accounts.spotify.com/authorize" in page and "<textarea" in page
    page = post(server.url + "/inloggen", {"adres": "http://127.0.0.1:8888/callback?code=AQB"}).read().decode()
    assert "Gelukt!" in page and "<textarea" not in page
    server.login.open = False  # al ingelogd: geen link, geen formulier
    page = urllib.request.urlopen(server.url + "/inloggen", timeout=5).read().decode()
    assert "accounts.spotify.com" not in page and "<textarea" not in page


def test_login_attempts_are_limited(server):
    from web import LOGIN_TRIES
    server.login = Login()
    for _ in range(LOGIN_TRIES):
        post(server.url + "/inloggen", {"adres": "fout"})
    post(server.url + "/inloggen", {"adres": "fout"})
    assert len(server.login.pasted) == LOGIN_TRIES  # de laatste kwam er niet meer door


def test_no_login_page_without_login(server):
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(server.url + "/inloggen", timeout=5)
    assert err.value.code == 404


def test_backup_download_and_restore(server):
    import json
    reply = urllib.request.urlopen(server.url + "/backup", timeout=5)
    assert "attachment" in reply.headers["Content-Disposition"]
    backup = json.loads(reply.read())
    assert backup["instellingen"] == {"idle_min": 5}

    def answer():
        answer.got = server.changes.get(timeout=5)
        server.changes.task_done()

    worker = threading.Thread(target=answer)
    worker.start()
    page = post(server.url + "/backup", {"bestand": json.dumps({"instellingen": {"idle_min": 1}})}).read().decode()
    worker.join(5)
    assert answer.got == ("idle_min", 1) and "ok" in page


def test_backup_restore_refuses_rubbish(server):
    import json
    page = post(server.url + "/backup", {"bestand": "dit is geen json"}).read().decode()
    assert "err" in page and server.changes.empty()
    page = post(server.url + "/backup", {"bestand": json.dumps({"idle_min": 99})}).read().decode()
    assert "err" in page and server.changes.empty()  # ongeldige waarde: overgeslagen
