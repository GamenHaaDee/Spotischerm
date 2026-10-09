"""QR-codes voor de Delen-pagina: het nummer of de playlist die speelt, en de gast-wifi."""
import pygame

try:
    import segno
except ImportError:  # oude installatie: bash install.sh opnieuw draaien
    segno = None

QUIET = 2          # witte rand om de code, in modules (de norm zegt 4, maar het vlak eromheen is ook wit)
SHAREABLE = ("track", "episode", "playlist", "album", "artist", "show")


def spotify_link(uri):
    """'spotify:playlist:abc' -> 'https://open.spotify.com/playlist/abc', of None als dat niet kan."""
    parts = (uri or "").split(":")
    if len(parts) != 3 or parts[0] != "spotify" or parts[1] not in SHAREABLE:
        return None  # bijv. Gelikete nummers (spotify:user:...:collection) hebben geen deelbare link
    return f"https://open.spotify.com/{parts[1]}/{parts[2]}"


def _escape(value):
    for ch in "\\;,:\"":
        value = value.replace(ch, "\\" + ch)
    return value


def wifi_payload(name, password, security="WPA"):
    """De tekst die telefoons herkennen als 'verbind met dit netwerk'."""
    security = (security or "WPA").strip().upper()
    if security in ("GEEN", "NONE", "NOPASS", "OPEN") or not password:
        return f"WIFI:T:nopass;S:{_escape(name)};;"
    if security not in ("WPA", "WEP"):
        security = "WPA"  # WPA2 en WPA3 heten in deze code allebei WPA
    return f"WIFI:T:{security};S:{_escape(name)};P:{_escape(password)};;"


class QrCache:
    """Maakt QR-codes als plaatje en onthoudt ze: opnieuw uitrekenen kost een trage Pi te veel."""

    available = segno is not None

    def __init__(self):
        self._made = {}

    def get(self, data, size):
        key = (data, size)
        if key not in self._made:
            if len(self._made) > 12:
                self._made.clear()
            self._made[key] = self._make(data, size)
        return self._made[key]

    @staticmethod
    def _make(data, size):
        matrix = segno.make(data, error="m", micro=False).matrix
        n = len(matrix) + 2 * QUIET
        small = pygame.Surface((n, n))
        small.fill((255, 255, 255))
        for y, row in enumerate(matrix):
            for x, dark in enumerate(row):
                if dark:
                    small.set_at((x + QUIET, y + QUIET), (0, 0, 0))
        # Hele pixels per module, zodat de code scherp blijft; wat overblijft wordt witte rand.
        step = max(1, size // n)
        out = pygame.Surface((size, size))
        out.fill((255, 255, 255))
        sharp = pygame.transform.scale(small, (n * step, n * step))
        out.blit(sharp, sharp.get_rect(center=(size // 2, size // 2)))
        return out
