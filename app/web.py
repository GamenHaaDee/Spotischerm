"""Instellingen via je telefoon: een kleine webpagina in het thuisnetwerk.

Alleen de keuzes van het tandwiel (weer, rustscherm, nachtmodus, ...); geen Spotify-sleutels
of wachtwoorden. Wijzigingen gaan via een wachtrij naar het scherm, dat ze zelf toepast.
"""
import html
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

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

    def __init__(self, port, describe, validate):
        super().__init__(daemon=True)
        self.port, self.describe, self.validate = port, describe, validate
        self.changes = queue.Queue()

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

            def do_GET(self):
                if urlsplit(self.path).path != "/":
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

        try:
            ThreadingHTTPServer(("", self.port), Handler).serve_forever()
        except OSError as err:
            print(f"Webpagina voor instellingen niet gestart (poort {self.port}): {err}", flush=True)
