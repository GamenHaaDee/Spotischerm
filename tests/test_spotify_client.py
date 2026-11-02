"""De Spotify-client: niet blijven hangen bij "te veel verzoeken", en de verzoekenteller."""
import json
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from spotipy.exceptions import SpotifyException

import common


@pytest.fixture
def fake_api():
    """Een klein servertje dat zich voordoet als de Spotify Web API. answer = (status, headers)."""
    state = {"hits": 0, "answer": (200, {})}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["hits"] += 1
            status, headers = state["answer"]
            body = json.dumps({"error": {"status": status, "message": "test"}} if status != 200
                              else {"is_playing": False}).encode()
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    client = common.Client(auth="nep", status_forcelist=(500, 502, 503, 504), retries=2, requests_timeout=5)
    client.prefix = f"http://127.0.0.1:{server.server_port}/v1/"
    yield client, state
    server.shutdown()


def test_normal_requests_are_counted(fake_api):
    client, state = fake_api
    client.current_playback()
    client.current_playback()
    assert state["hits"] == 2
    hour, today, _ = common.counter.counts()
    assert (hour, today) == (2, 2)


def test_quota_exceeded_does_not_hang(fake_api):
    client, state = fake_api
    state["answer"] = (429, {"Retry-After": "37619"})
    started = time.monotonic()
    for _ in range(3):
        with pytest.raises(SpotifyException) as err:
            client.current_playback()
        assert err.value.http_status == 429
    assert time.monotonic() - started < 3  # spotipy/urllib3 mogen niet uren gaan wachten
    assert state["hits"] == 1  # daarna stuurt de client niets meer
    assert common.wait_left() > 37000
    assert float(common.WAIT_PATH.read_text()) > time.time() + 37000  # bewaard voor na een herstart
    assert common.counter.counts()[1] == 1  # geblokkeerde pogingen tellen niet


def test_waiting_ends_by_itself(fake_api, monkeypatch):
    client, state = fake_api
    monkeypatch.setattr(common, "_blocked_until", time.time() - 1)
    client.current_playback()
    assert state["hits"] == 1


# -- de teller zelf --

def at(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M")


def test_counter_rolls_over_hours_and_days(tmp_path):
    c = common.RequestCounter(tmp_path / "teller")
    for _ in range(3):
        c.add(at("2026-11-02 09:10"))
    c.add(at("2026-11-02 10:05"))
    assert c.counts(at("2026-11-02 10:30")) == (1, 4, 0)
    c.add(at("2026-11-03 00:01"))
    assert c.counts(at("2026-11-03 00:02")) == (1, 1, 4)  # gisteren = de vorige dag
    assert c.counts(at("2026-11-05 12:00")) == (0, 0, 0)  # een dag overgeslagen: gisteren onbekend


def test_counter_survives_a_restart(tmp_path):
    path = tmp_path / "teller"
    c = common.RequestCounter(path)
    c.add(at("2026-11-02 09:10"))  # eerste keer: meteen bewaard
    c.add(at("2026-11-02 09:11"))
    c._save()
    again = common.RequestCounter(path)
    assert again.counts(at("2026-11-02 09:20")) == (2, 2, 0)
