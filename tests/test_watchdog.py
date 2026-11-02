"""Zelfherstel: de app meldt aan systemd dat hij leeft (via $NOTIFY_SOCKET)."""
import socket

import pytest

import watchdog

pytestmark = pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="geen Unix-sockets")


@pytest.fixture
def systemd(tmp_path, monkeypatch):
    """Een socket die doet alsof hij systemd is."""
    path = str(tmp_path / "notify")
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.bind(path)
    except OSError:
        pytest.skip("Unix-datagramsockets werken hier niet (Windows)")
    sock.settimeout(2)
    monkeypatch.setenv("NOTIFY_SOCKET", path)
    yield sock
    sock.close()


def test_start_turns_the_watchdog_on(systemd):
    assert watchdog.start(90)
    assert systemd.recv(200).decode() == "WATCHDOG_USEC=90000000\nWATCHDOG=1"


def test_alive_is_not_sent_too_often(systemd, monkeypatch):
    watchdog.start()
    systemd.recv(200)
    watchdog.alive()  # net gemeld: nu niets
    monkeypatch.setattr(watchdog, "_last", watchdog._last - watchdog.PING_EVERY)
    watchdog.alive()
    assert systemd.recv(200).decode() == "WATCHDOG=1"


def test_without_systemd_nothing_happens(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    assert watchdog.start() is False
    watchdog.alive()  # geen fout
