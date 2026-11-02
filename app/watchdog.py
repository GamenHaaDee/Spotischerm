"""Zelfherstel: loopt de app vast, dan herstart systemd hem vanzelf.

De app meldt elke paar seconden aan systemd dat hij nog leeft ("WATCHDOG=1", via de socket in
$NOTIFY_SOCKET; geen extra pakketten nodig). Blijft dat langer dan TIMEOUT seconden uit, dan
herstart systemd de app.

De app zet de watchdog zelf aan bij het starten (WATCHDOG_USEC), niet spotischerm.service. Zo kan een
oudere versie zonder watchdog (na "Vorige versie terugzetten") gewoon draaien: die meldt niets, en
dan let systemd ook niet op. De service hoeft alleen NotifyAccess=main te hebben.
Buiten systemd (op de pc) doet dit allemaal niets.
"""
import os
import socket
import time

TIMEOUT = 90      # zo lang (s) mag de app niets laten horen voor systemd hem herstart
PING_EVERY = 10   # zo vaak (s) melden dat hij nog leeft

_last = 0.0


def _send(message):
    path = os.environ.get("NOTIFY_SOCKET")
    if not path or not hasattr(socket, "AF_UNIX"):
        return False
    if path.startswith("@"):  # abstracte socket
        path = "\0" + path[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(path)
            sock.sendall(message.encode())
        return True
    except OSError:
        return False


def start(timeout=TIMEOUT):
    """Watchdog aanzetten (of de tijd veranderen). True als systemd meeluistert."""
    global _last
    _last = time.monotonic()
    return _send(f"WATCHDOG_USEC={int(timeout * 1_000_000)}\nWATCHDOG=1")


def alive():
    """Vanuit de hoofdlus: "ik leef nog", hoogstens eens per PING_EVERY seconden."""
    global _last
    now = time.monotonic()
    if now - _last >= PING_EVERY:
        _last = now
        _send("WATCHDOG=1")
