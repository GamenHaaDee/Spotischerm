"""Kleine webpagina's in het thuisnetwerk: instellingen via je telefoon, en verzoekjes van gasten.

Instellingen: alleen de keuzes van het tandwiel (weer, rustscherm, nachtmodus, ...); geen
Spotify-sleutels of wachtwoorden. Wijzigingen gaan via een wachtrij naar het scherm.
Verzoekjes (/verzoekjes): gasten zoeken een nummer en zetten het in de wachtrij.
Schermafdruk (/scherm.png): wat nu op het scherm staat, als plaatje.
Inloggen (/inloggen): bij Spotify inloggen via je telefoon, zie login.py.
Back-up (/backup): je scherminstellingen downloaden en weer terugzetten, bijv. na een nieuwe SD-kaart.
Alleen wat je via deze pagina ook kunt instellen: nooit Spotify-sleutels, je login of wachtwoorden.
"""
import json
import re
import html
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

from i18n import language, tr

PAGE = """<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpotiScherm</title>
<style>
:root {{ --bg:#121212; --panel:#2a2a2a; --text:#f0f0f0; --muted:#a0a0a0; --accent:{accent}; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:16px/1.4 system-ui,sans-serif; }}
main {{ max-width:520px; margin:0 auto; padding:16px; }}
h1 {{ font-size:22px; margin:8px 0 4px; }}
p.sub {{ color:var(--muted); margin:0 0 16px; }}
fieldset {{ border:0; background:var(--panel); border-radius:14px; padding:12px 14px; margin:0 0 12px; }}
fieldset {{ min-width:0; }}
legend {{ padding:0; margin:0 0 8px; font-weight:600; }}
label.opt {{ display:inline-block; margin:0 6px 8px 0; }}
label.opt input {{ position:absolute; opacity:0; }}
label.opt span {{ display:inline-block; padding:8px 14px; border-radius:999px; background:#404040; }}
label.opt input:checked + span {{ background:var(--accent); color:#121212; font-weight:600; }}
label.opt input:focus-visible + span {{ outline:2px solid var(--text); outline-offset:2px; }}
input[type=text], input[type=time] {{ width:100%; padding:10px 12px; border-radius:10px; border:0;
  background:#404040; color:var(--text); font:inherit; }}
.row {{ display:flex; gap:10px; }} .row > div {{ flex:1; }}
.row small {{ color:var(--muted); display:block; margin-bottom:4px; }}
button {{ width:100%; padding:14px; border:0; border-radius:999px; background:var(--accent); color:#121212;
  font:600 17px system-ui,sans-serif; margin:4px 0 24px; }}
.ok {{ background:#1e3a26; color:#bff5cf; padding:10px 14px; border-radius:10px; margin-bottom:12px; }}
.err {{ background:#4a1f1f; color:#ffd0d0; padding:10px 14px; border-radius:10px; margin-bottom:12px; }}
a.shot, label.shot {{ display:block; text-align:center; padding:14px; border-radius:999px; background:var(--panel);
  color:var(--text); text-decoration:none; font-weight:600; margin:0 0 12px; cursor:pointer; }}
p.note {{ color:var(--muted); font-size:14px; margin:0 0 24px; }}
</style></head><body><main>
<h1>SpotiScherm</h1><p class="sub">{subtitle}</p>
{notice}
<form method="post">{fields}<button type="submit">{save}</button></form>
<a class="shot" href="/scherm.png">{shot}</a>
<h2 style="font-size:18px;margin:24px 0 8px">{backup}</h2>
<a class="shot" href="/backup" download>{download}</a>
<form method="post" action="/backup" id="herstel">
<label class="shot">{restore}<input type="file" accept=".json,application/json" id="kies" hidden></label>
<input type="hidden" name="bestand" id="inhoud"></form>
<p class="note">{backup_note}</p>
<script>
document.getElementById("kies").onchange = function (e) {{
  var file = e.target.files[0];
  if (!file) return;
  file.text().then(function (text) {{
    document.getElementById("inhoud").value = text;
    document.getElementById("herstel").submit();
  }});
}};
</script>
</main></body></html>"""


REQUEST_MAX = 3              # zoveel verzoekjes per gast (IP-adres) ...
REQUEST_WINDOW = 15 * 60     # ... per kwartier
TRACK_URI = re.compile(r"^spotify:track:[A-Za-z0-9]{22}$")

REQUEST_PAGE = """<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#121212; --panel:#2a2a2a; --text:#f0f0f0; --muted:#a0a0a0; --accent:{accent}; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:16px/1.4 system-ui,sans-serif; }}
main {{ max-width:520px; margin:0 auto; padding:16px; }}
h1 {{ font-size:22px; margin:8px 0 4px; }}
p.sub {{ color:var(--muted); margin:0 0 14px; }}
.now {{ background:var(--panel); border-radius:14px; padding:10px 14px; margin-bottom:14px; }}
.now small {{ color:var(--muted); display:block; }}
form.search {{ display:flex; gap:8px; margin-bottom:14px; }}
form.search input {{ flex:1; min-width:0; padding:12px; border-radius:999px; border:0; background:#404040;
  color:var(--text); font:inherit; }}
button {{ border:0; border-radius:999px; background:var(--accent); color:#121212; font:600 16px system-ui,sans-serif;
  padding:12px 16px; }}
ul {{ list-style:none; padding:0; margin:0; }}
li {{ display:flex; align-items:center; gap:10px; background:var(--panel); border-radius:12px; padding:8px; margin-bottom:8px; }}
li img {{ width:48px; height:48px; border-radius:6px; flex:none; background:#404040; }}
li div {{ flex:1; min-width:0; }}
li b, li small {{ display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
li small {{ color:var(--muted); }}
li button {{ padding:10px 14px; }}
.ok {{ background:#1e3a26; color:#bff5cf; padding:10px 14px; border-radius:10px; margin-bottom:12px; }}
.err {{ background:#4a1f1f; color:#ffd0d0; padding:10px 14px; border-radius:10px; margin-bottom:12px; }}
</style></head><body><main>
<h1>{title}</h1><p class="sub">{subtitle}</p>
{now}{notice}
<form class="search" method="get" action="/verzoekjes">
<input type="search" name="q" value="{query}" placeholder="{placeholder}" autofocus>
<button type="submit">{search}</button></form>
{results}
</main></body></html>"""


LOGIN_TRIES = 10  # zoveel inlogpogingen per telefoon (IP-adres) per kwartier

LOGIN_PAGE = """<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#121212; --panel:#2a2a2a; --text:#f0f0f0; --muted:#a0a0a0; --accent:{accent}; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:16px/1.45 system-ui,sans-serif; }}
main {{ max-width:520px; margin:0 auto; padding:16px; }}
h1 {{ font-size:22px; margin:8px 0 14px; }}
ol {{ padding-left:22px; margin:0 0 16px; }}
li {{ margin-bottom:12px; }}
li small {{ color:var(--muted); display:block; }}
a.btn, button {{ display:inline-block; border:0; border-radius:999px; background:var(--accent); color:#121212;
  font:600 16px system-ui,sans-serif; padding:12px 18px; text-decoration:none; margin-top:6px; }}
textarea {{ width:100%; min-height:90px; padding:10px 12px; border-radius:10px; border:0; background:#404040;
  color:var(--text); font:14px/1.3 ui-monospace,monospace; margin-top:6px; }}
.ok {{ background:#1e3a26; color:#bff5cf; padding:10px 14px; border-radius:10px; margin-bottom:12px; }}
.err {{ background:#4a1f1f; color:#ffd0d0; padding:10px 14px; border-radius:10px; margin-bottom:12px; }}
</style></head><body><main>
<h1>{title}</h1>
{notice}{body}
</main></body></html>"""


def _render_requests(results, query):
    rows = []
    for r in results:
        img = f'<img src="{html.escape(r["image"])}" alt="">' if r.get("image") else "<img alt=\"\">"
        rows.append(
            f'<li>{img}<div><b>{html.escape(r["name"])}</b><small>{html.escape(r["artist"])}</small></div>'
            f'<form method="post" action="/verzoekjes"><input type="hidden" name="uri" value="{html.escape(r["uri"])}">'
            f'<input type="hidden" name="name" value="{html.escape(r["name"])}">'
            f'<input type="hidden" name="q" value="{html.escape(query)}">'
            f'<button type="submit" aria-label="{html.escape(tr("In de wachtrij"))}">+</button></form></li>')
    return "<ul>" + "".join(rows) + "</ul>" if rows else ""


def _choice(field, current):
    opts = "".join(
        f'<label class="opt"><input type="radio" name="{field["key"]}" value="{html.escape(str(v))}"'
        f'{" checked" if str(v) == str(current) else ""}><span>{html.escape(label)}</span></label>'
        for v, label in field["options"])
    return f'<fieldset><legend>{html.escape(field["label"])}</legend>{opts}</fieldset>'


def _render(fields, settings, notice):
    parts, times = [], []
    for f in fields:
        current = settings.get(f["key"], "")
        if f["type"] == "choice":
            parts.append(_choice(f, current))
        elif f["type"] == "text":
            parts.append(f'<fieldset><legend>{html.escape(f["label"])}</legend>'
                         f'<input type="text" name="{f["key"]}" maxlength="60" value="{html.escape(str(current))}"'
                         f' placeholder="{html.escape(f.get("placeholder", ""))}"></fieldset>')
        elif f["type"] == "time":
            times.append(f'<div><small>{html.escape(f["label"])}</small>'
                         f'<input type="time" name="{f["key"]}" value="{html.escape(str(current))}"></div>')
            if f.get("last"):
                parts.append(f'<fieldset><legend>{html.escape(f["group"])}</legend>'
                             f'<div class="row">{"".join(times)}</div></fieldset>')
                times = []
    return "".join(parts)


class SettingsServer(threading.Thread):
    """describe() -> (velden, huidige instellingen, accentkleur); wijzigingen komen in self.changes."""

    def __init__(self, port, describe, validate, guests=None, login=None):
        super().__init__(daemon=True)
        self.port, self.describe, self.validate = port, describe, validate
        # guests: object met search(query), add(uri, name) -> (gelukt, melding) en now() -> tekst of None
        self.guests = guests
        self.login = login  # login.PhoneLogin, of None = niet via de telefoon inloggen
        self.changes = queue.Queue()
        # Schermafdruk: de webthread vraagt erom, het scherm maakt hem bij het volgende beeld (take_shot).
        self.shot_wanted, self.shot_ready = threading.Event(), threading.Event()
        self.shot, self.shot_lock = None, threading.Lock()
        self.request_log = {}    # IP-adres -> tijden van verzoekjes
        self.log_lock = threading.Lock()

    def take_shot(self, surface, save):
        """Vanuit de hoofdlus: als iemand om een schermafdruk vroeg, nu het beeld als PNG bewaren."""
        if self.shot_wanted.is_set():
            self.shot_wanted.clear()
            self.shot = save(surface)
            self.shot_ready.set()

    def screenshot(self):
        """PNG van het scherm, of None als het scherm niet op tijd antwoordt."""
        with self.shot_lock:
            self.shot_ready.clear()
            self.shot_wanted.set()
            if not self.shot_ready.wait(5):
                self.shot_wanted.clear()
                return None
            data, self.shot = self.shot, None  # niets bewaren: elke schermafdruk is nieuw
            return data

    def request_allowed(self, ip, kind="verzoekje", limit=REQUEST_MAX):
        """Mag deze telefoon dit nog een keer (verzoekje, inlogpoging)? Zo niet: hoeveel minuten wachten."""
        now = time.time()
        with self.log_lock:
            recent = [t for t in self.request_log.get((kind, ip), []) if now - t < REQUEST_WINDOW]
            self.request_log[(kind, ip)] = recent
            if len(recent) >= limit:
                return False, int((REQUEST_WINDOW - (now - recent[0])) // 60) + 1
            recent.append(now)
            return True, 0

    def run(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # geen regel per verzoek in het logboek
                pass

            def send_page(self, notice=""):
                fields, settings, accent = server.describe()
                body = PAGE.format(lang=language(), accent=accent, notice=notice,
                                   subtitle=html.escape(tr("Instellingen via je telefoon")),
                                   fields=_render(fields, settings, notice), save=html.escape(tr("Opslaan")),
                                   shot=html.escape("📸 " + tr("Schermafdruk maken")),
                                   backup=html.escape(tr("Back-up")),
                                   download=html.escape("⬇ " + tr("Download je instellingen")),
                                   restore=html.escape("⬆ " + tr("Terugzetten uit een bestand")),
                                   backup_note=html.escape(tr("Alleen je scherminstellingen: geen wachtwoorden en "
                                                              "geen Spotify-login.")))
                data = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def send_html(self, body, status=200):
                data = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def send_requests(self, query="", notice=""):
                guests = server.guests
                _, _, accent = server.describe()
                results = []
                if query:
                    try:
                        results = guests.search(query)
                    except Exception as err:  # Spotify even weg
                        print(f"Verzoekjes zoeken: {err}", flush=True)
                        notice += f'<div class="err">{html.escape(tr("Zoeken lukt nu niet, probeer het zo opnieuw."))}</div>'
                    if not results and not notice:
                        notice = f'<div class="err">{html.escape(tr("Niks gevonden. Probeer een andere zoekterm."))}</div>'
                now = guests.now()
                now_html = (f'<div class="now"><small>{html.escape(tr("Nu speelt"))}</small>{html.escape(now)}</div>'
                            if now else "")
                self.send_html(REQUEST_PAGE.format(
                    lang=language(), accent=accent, title=html.escape(tr("Verzoekjes")),
                    subtitle=html.escape(tr("Zoek een nummer en zet het in de wachtrij.")), now=now_html,
                    notice=notice, query=html.escape(query), placeholder=html.escape(tr("Nummer of artiest")),
                    search=html.escape(tr("Zoek")), results=_render_requests(results, query)))

            def do_GET(self):
                url = urlsplit(self.path)
                if url.path == "/verzoekjes" and server.guests:
                    params = {k: v[-1] for k, v in parse_qs(url.query).items()}
                    added = params.get("ok", "")
                    notice = (f'<div class="ok">{html.escape(tr("In de wachtrij: {name}", name=added))}</div>'
                              if added else "")
                    self.send_requests(params.get("q", "").strip()[:80], notice)
                    return
                if url.path == "/scherm.png":
                    self.send_shot()
                    return
                if url.path == "/inloggen" and server.login:
                    self.send_login()
                    return
                if url.path == "/backup":
                    self.send_backup()
                    return
                if url.path != "/":
                    self.send_error(404)
                    return
                saved = "ok=1" in (urlsplit(self.path).query or "")
                self.send_page(f'<div class="ok">{html.escape(tr("Opgeslagen"))}</div>' if saved else "")

            def send_shot(self):
                data = server.screenshot()
                if data is None:
                    self.send_error(503)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Disposition",
                                 f'inline; filename="spotischerm-{time.strftime("%Y%m%d-%H%M%S")}.png"')
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def send_backup(self):
                fields, settings, _ = server.describe()
                data = {"app": "SpotiScherm", "datum": time.strftime("%Y-%m-%d"),
                        "instellingen": {f["key"]: settings[f["key"]] for f in fields if f["key"] in settings}}
                body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="spotischerm-instellingen-{time.strftime("%Y-%m-%d")}.json"')
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def post_backup(self, form):
                """Een back-up terugzetten: elke waarde gaat door dezelfde controle als het formulier."""
                try:
                    data = json.loads(form.get("bestand", ""))
                    if isinstance(data, dict) and isinstance(data.get("instellingen"), dict):
                        data = data["instellingen"]  # onze back-up; anders een los instellingen.json
                    if not isinstance(data, dict):
                        raise ValueError
                except ValueError:
                    self.send_page(f'<div class="err">{html.escape(tr("Dit is geen back-up van SpotiScherm."))}</div>')
                    return
                fields, settings, _ = server.describe()
                changes, bad = [], []
                for f in fields:
                    if f["key"] not in data:
                        continue
                    value = server.validate(f["key"], str(data[f["key"]]).strip())
                    if value is None:
                        bad.append(f["label"])
                    elif value != settings.get(f["key"]):
                        changes.append((f["key"], value))
                if not changes and not bad and not any(f["key"] in data for f in fields):
                    self.send_page(f'<div class="err">{html.escape(tr("Dit is geen back-up van SpotiScherm."))}</div>')
                    return
                for change in changes:
                    server.changes.put(change)
                for _ in range(60):  # even wachten tot het scherm ze heeft toegepast
                    if not server.changes.unfinished_tasks:
                        break
                    time.sleep(0.05)
                notice = f'<div class="ok">{html.escape(tr("Teruggezet: {n} instellingen", n=len(changes)))}</div>'
                if bad:
                    notice += (f'<div class="err">{html.escape(tr("Overgeslagen (ongeldig)"))}: '
                               f'{html.escape(", ".join(bad))}</div>')
                self.send_page(notice)

            def send_login(self, notice="", done=False):
                login, _, _, accent = server.login, *server.describe()
                if done:
                    body = ""
                elif not login.allowed():
                    body = f'<p>{html.escape(tr("Je bent al ingelogd. Wil je een ander account? Kies op het scherm Instellingen → Spotify-account → Opnieuw inloggen, en open deze pagina dan opnieuw."))}</p>'
                else:
                    steps = [
                        (tr("Tik op de knop en log in bij Spotify. Tik daarna op Akkoord."),
                         f'<a class="btn" href="{html.escape(login.url())}" target="_blank" rel="noopener">'
                         f'{html.escape(tr("Inloggen bij Spotify"))}</a>'),
                        (tr("Je komt op een pagina die niet laadt (127.0.0.1). Dat hoort zo."),
                         f'<small>{html.escape(tr("Kopieer het hele adres uit de adresbalk van die pagina."))}</small>'),
                        (tr("Plak dat adres hier en tik op Klaar."),
                         '<form method="post" action="/inloggen">'
                         f'<textarea name="adres" required placeholder="http://127.0.0.1:8888/callback?code=…"></textarea>'
                         f'<button type="submit">{html.escape(tr("Klaar"))}</button></form>'),
                    ]
                    body = "<ol>" + "".join(f"<li>{html.escape(text)}{extra}</li>" for text, extra in steps) + "</ol>"
                self.send_html(LOGIN_PAGE.format(lang=language(), accent=accent, notice=notice, body=body,
                                                 title=html.escape(tr("Inloggen bij Spotify"))))

            def post_login(self, form):
                allowed, wait = server.request_allowed(self.client_address[0], "inloggen", LOGIN_TRIES)
                if not allowed:
                    self.send_login(f'<div class="err">{html.escape(tr("Te veel pogingen. Probeer het over {minutes} min opnieuw.", minutes=wait))}</div>')
                    return
                ok, message = server.login.finish(form.get("adres", "")[:2000])
                self.send_login(f'<div class="{"ok" if ok else "err"}">{html.escape(message)}</div>', done=ok)

            def do_POST(self):
                # Alleen formulieren van deze pagina zelf, niet van een andere website.
                origin = self.headers.get("Origin")
                if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                    self.send_error(403)
                    return
                length = min(int(self.headers.get("Content-Length") or 0), 10_000)
                form = {k: v[-1] for k, v in parse_qs(self.rfile.read(length).decode("utf-8")).items()}
                if urlsplit(self.path).path == "/verzoekjes" and server.guests:
                    self.post_request(form)
                    return
                if urlsplit(self.path).path == "/inloggen" and server.login:
                    self.post_login(form)
                    return
                if urlsplit(self.path).path == "/backup":
                    self.post_backup(form)
                    return
                fields, settings, _ = server.describe()
                bad, changes = [], []
                for f in fields:
                    if f["key"] not in form:
                        continue
                    value = server.validate(f["key"], form[f["key"]].strip())
                    if value is None:
                        bad.append(f["label"])
                    elif value != settings.get(f["key"]):
                        changes.append((f["key"], value))
                if bad:
                    self.send_page(f'<div class="err">{html.escape(tr("Ongeldige waarde"))}: '
                                   f'{html.escape(", ".join(bad))}</div>')
                    return
                for change in changes:
                    server.changes.put(change)
                # Even wachten tot het scherm ze heeft toegepast, dan toont de pagina meteen de nieuwe stand.
                for _ in range(60):
                    if not server.changes.unfinished_tasks:
                        break
                    time.sleep(0.05)
                self.send_response(303)
                self.send_header("Location", "/?ok=1")
                self.end_headers()

            def post_request(self, form):
                uri, name, query = form.get("uri", ""), form.get("name", "")[:100], form.get("q", "")[:80]
                if not TRACK_URI.match(uri):
                    self.send_error(400)
                    return
                allowed, wait = server.request_allowed(self.client_address[0])
                if not allowed:
                    self.send_requests(query, f'<div class="err">{html.escape(tr("Even rustig aan: over {minutes} min mag je weer een nummer kiezen.", minutes=wait))}</div>')
                    return
                ok, message = server.guests.add(uri, name)
                if not ok:
                    self.send_requests(query, f'<div class="err">{html.escape(message)}</div>')
                    return
                self.send_response(303)
                self.send_header("Location", f"/verzoekjes?q={quote(query)}&ok={quote(name)}")
                self.end_headers()

        try:
            ThreadingHTTPServer(("", self.port), Handler).serve_forever()
        except OSError as err:
            print(f"Webpagina voor instellingen niet gestart (poort {self.port}): {err}", flush=True)
