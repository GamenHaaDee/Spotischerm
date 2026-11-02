"""Inloggen bij Spotify via je telefoon, zonder SSH en zonder auth.py.

Spotify stuurt je na het inloggen naar het adres dat bij je Spotify-app hoort
(http://127.0.0.1:8888/callback). Dat kan je telefoon niet bereiken, dus die toont een foutpagina;
het adres van die pagina bevat de code. Die plak je terug op de telefoonpagina (/inloggen), en de Pi
maakt er een login van. Net als auth.py, maar dan in de browser van je telefoon.

Veiligheid: iedereen in je wifi kan de telefoonpagina openen. Inloggen kan daarom alleen als er nog
niemand is ingelogd, of vlak nadat je op het scherm zelf "Opnieuw inloggen" hebt gekozen. En alleen
de inlogpoging die de Pi zelf begon telt (een willekeurige 'state' in de link).
"""
import os
import secrets
import threading
import time
from urllib.parse import parse_qs, urlsplit

from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

from common import CACHE_PATH, SCOPES, load_config
from i18n import tr

LOGIN_WINDOW = 10 * 60  # na "Opnieuw inloggen" op het scherm: zo lang (s) mag het via de telefoon


def code_from(pasted):
    """Code en state uit het geplakte adres (of alleen de code). (None, None) als er niets in staat."""
    text = (pasted or "").strip()
    if not text:
        return None, None
    query = parse_qs(urlsplit(text).query) if "?" in text or "://" in text else {}
    if "code" in query:
        return query["code"][-1], (query.get("state") or [None])[-1]
    if " " in text or "/" in text or "=" in text:
        return None, None
    return text, None  # alleen de code geplakt


class PhoneLogin:
    def __init__(self, cache_path=CACHE_PATH):
        self.cache_path = cache_path
        self.lock = threading.Lock()
        self.open_until = 0.0
        self.state = None
        self.done = False  # gezet zodra het inloggen gelukt is; het scherm gaat dan verder

    def allowed(self):
        """Mag er nu via de telefoon worden ingelogd?"""
        return not self.cache_path.exists() or time.monotonic() < self.open_until

    def open(self):
        """Vanaf het scherm: opnieuw inloggen toestaan, even."""
        with self.lock:
            self.open_until = time.monotonic() + LOGIN_WINDOW
            self.state = None

    def minutes_left(self):
        return max(0, int((self.open_until - time.monotonic()) // 60) + 1) if self.cache_path.exists() else None

    def _oauth(self):
        load_config()
        return SpotifyOAuth(client_id=os.environ["SPOTIFY_CLIENT_ID"],
                            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                            redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
                            scope=SCOPES, cache_path=str(self.cache_path), open_browser=False, state=self.state)

    def url(self):
        """De inloglink van Spotify, met een eigen state voor deze poging."""
        with self.lock:
            if not self.state:
                self.state = secrets.token_urlsafe(16)
            return self._oauth().get_authorize_url()

    def finish(self, pasted):
        """Het geplakte adres omzetten in een login. Geeft (gelukt, melding)."""
        if not self.allowed():
            return False, tr("Inloggen via je telefoon staat nu dicht. Kies op het scherm Instellingen → "
                             "Spotify-account → Opnieuw inloggen.")
        code, state = code_from(pasted)
        if not code:
            return False, tr("Daar staat geen code in. Kopieer het hele adres uit de adresbalk.")
        with self.lock:
            if not self.state or (state and state != self.state):
                return False, tr("Dit adres hoort niet bij deze inlogpoging. Tik opnieuw op Inloggen bij Spotify.")
            oauth = self._oauth()
            try:
                oauth.get_access_token(code, as_dict=False, check_cache=False)  # schrijft .spotify-cache
            except SpotifyOauthError:
                return False, tr("Spotify accepteert deze code niet (verlopen of al gebruikt). "
                                 "Tik opnieuw op Inloggen bij Spotify.")
            except Exception as err:  # geen internet, Spotify even weg
                print(f"Inloggen via telefoon: {err}", flush=True)
                return False, tr("Inloggen lukt nu niet. Probeer het zo opnieuw.")
            self.state, self.open_until, self.done = None, 0.0, True
        return True, tr("Gelukt! Je bent ingelogd. Het scherm gaat nu verder.")
