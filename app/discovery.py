"""Speakers in je eigen netwerk vinden, zoals de Spotify-app op je telefoon dat doet.

De Spotify Web API kent Google Cast-speakers alleen terwijl Spotify erop draait.
Hier zoeken we ze zelf via mDNS, zodat het scherm ze in elk geval kan tonen.
"""
import threading

import requests

try:
    from zeroconf import IPVersion, ServiceBrowser, Zeroconf
except ImportError:  # zonder zeroconf werkt de rest van de app gewoon
    Zeroconf = None

CAST = "_googlecast._tcp.local."
CONNECT = "_spotify-connect._tcp.local."


def norm(name):
    return " ".join(name.casefold().split())


class LocalDevices:
    def __init__(self):
        self.lock = threading.Lock()
        self._cast = {}      # servicenaam -> {name, kind, ip}
        self._connect = {}   # servicenaam -> {name, ip}
        if Zeroconf is None:
            print("zeroconf niet geinstalleerd: speakers in het netwerk worden niet gezocht", flush=True)
            return
        self._zc = Zeroconf()
        ServiceBrowser(self._zc, [CAST, CONNECT], self)

    # -- zeroconf-callbacks --

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name, 3000)
        if not info:
            return
        props = {k.decode(): (v or b"").decode(errors="ignore") for k, v in info.properties.items()}
        ips = info.parsed_addresses(IPVersion.V4Only)
        ip = ips[0] if ips else None
        if type_ == CAST:
            model = props.get("md", "")
            kind = "group" if model == "Google Cast Group" else "tv" if "tv" in model.casefold() else "speaker"
            with self.lock:
                self._cast[name] = {"name": props.get("fn") or name.split(".")[0], "kind": kind, "ip": ip}
        elif ip:
            # Spotify Connect-apparaten noemen zich pas bij naam via hun eigen getInfo.
            path = props.get("CPath", "/")
            threading.Thread(target=self._ask_name, args=(name, ip, info.port, path), daemon=True).start()

    update_service = add_service

    def remove_service(self, zc, type_, name):
        with self.lock:
            self._cast.pop(name, None)
            self._connect.pop(name, None)

    def _ask_name(self, service, ip, port, path):
        try:
            r = requests.get(f"http://{ip}:{port}{path}", params={"action": "getInfo"}, timeout=3)
            data = r.json()
        except (requests.RequestException, ValueError):
            return
        if data.get("remoteName"):
            with self.lock:
                self._connect[service] = {"name": data["remoteName"], "ip": ip,
                                          "tv": data.get("deviceType") == "TV"}

    # -- voor het scherm --

    def snapshot(self):
        """Lijst van {name, kind, aliases}: één regel per apparaat, ook als het op twee manieren adverteert."""
        with self.lock:
            casts, connects = list(self._cast.values()), list(self._connect.values())
        devices = {}
        for c in casts:
            devices.setdefault(norm(c["name"]), {"name": c["name"], "kind": c["kind"],
                                                 "aliases": {norm(c["name"])}, "ip": c["ip"]})
        for c in connects:
            # Een tv met Cast én Spotify Connect: samenvoegen op IP-adres (groepen niet,
            # die delen hun IP met een van de speakers).
            twin = next((d for d in devices.values() if d["ip"] == c["ip"] and d["kind"] != "group"), None)
            if twin:
                twin["aliases"].add(norm(c["name"]))
                if c["tv"]:
                    twin["kind"] = "tv"
            else:
                devices.setdefault(norm(c["name"]), {"name": c["name"], "kind": "tv" if c["tv"] else "connect",
                                                     "aliases": {norm(c["name"])}, "ip": c["ip"]})
        return list(devices.values())
