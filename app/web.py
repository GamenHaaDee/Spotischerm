"""Kleine webpagina's in het thuisnetwerk: instellingen via je telefoon, en verzoekjes van gasten.

Instellingen: alleen de keuzes van het tandwiel (weer, rustscherm, nachtmodus, ...); geen
Spotify-sleutels of wachtwoorden. Wijzigingen gaan via een wachtrij naar het scherm.
Verzoekjes (/verzoekjes): gasten zoeken een nummer en zetten het in de wachtrij.
"""
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
</style></head><body><main>
<h1>SpotiScherm</h1><p class="sub">{subtitle}</p>
{notice}
<form method="post">{fields}<button type="submit">{save}</button></form>
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

    def __init__(self, port, describe, validate, guests=None):
        super().__init__(daemon=True)
        self.port, self.describe, self.validate = port, describe, validate
        # guests: object met search(query), add(uri, name) -> (gelukt, melding) en now() -> tekst of None
        self.guests = guests
        self.changes = queue.Queue()
        self.request_log = {}    # IP-adres -> tijden van verzoekjes
        self.log_lock = threading.Lock()

    def request_allowed(self, ip):
        """Mag deze gast nog een verzoekje doen? Zo niet: hoeveel minuten wachten."""
        now = time.time()
        with self.log_lock:
            recent = [t for t in self.request_log.get(ip, []) if now - t < REQUEST_WINDOW]
            self.request_log[ip] = recent
            if len(recent) >= REQUEST_MAX:
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
                                   fields=_render(fields, settings, notice), save=html.escape(tr("Opslaan")))
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
                if url.path != "/":
                    self.send_error(404)
                    return
                saved = "ok=1" in (urlsplit(self.path).query or "")
                self.send_page(f'<div class="ok">{html.escape(tr("Opgeslagen"))}</div>' if saved else "")

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
