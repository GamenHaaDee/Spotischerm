"""Weer voor het klokscherm, via Open-Meteo (gratis, geen account nodig)."""
import threading

import requests

from i18n import language, tr

REFRESH_SECONDS = 15 * 60
RETRY_SECONDS = 60

# WMO-weercodes, oplopend: de eerste grens waar de code onder valt, wint.
CODES = (
    (0, "Helder"), (1, "Overwegend helder"), (2, "Half bewolkt"), (3, "Bewolkt"),
    (48, "Mist"), (57, "Motregen"), (65, "Regen"), (67, "IJzel"), (77, "Sneeuw"),
    (82, "Regenbuien"), (86, "Sneeuwbuien"), (99, "Onweer"),
)


class PlaceNotFound(Exception):
    pass


def describe_code(code):
    for limit, text in CODES:
        if code <= limit:
            return tr(text)
    return ""


def rain_forecast(now_iso, hourly):
    """Regen in de komende uren als (soort, tijd, kans); de tekst maken we pas bij het tonen."""
    times, probs = hourly["time"], hourly["precipitation_probability"]
    start = next((i for i, t in enumerate(times) if t.startswith(now_iso[:13])), 0)
    window = list(zip(times[start:start + 4], probs[start:start + 4]))
    for i, (t, p) in enumerate(window):
        if p is not None and p >= 50:
            return ("now", None, p) if i == 0 else ("later", t[11:16], p)
    top = max((p or 0 for _, p in window), default=0)
    return ("slight", None, top) if top >= 20 else ("dry", None, 0)


def rain_text(forecast):
    kind, time, p = forecast
    return {"now": tr("Nu kans op regen ({p}%)", p=p),
            "later": tr("Regen verwacht rond {time} ({p}%)", time=time, p=p),
            "slight": tr("Kleine kans op regen ({p}%)", p=p),
            "dry": tr("Droog de komende uren")}[kind]


class Weather:
    """Haalt elk kwartier het weer op. De plaats mag tijdens het draaien veranderen."""

    def __init__(self, place, country="NL"):
        self.place, self.country = place, country
        self._now = None         # (temperatuur, weercode, max, min)
        self._rain = None
        self._error = None
        self._coords = None      # (plaats, lat, lon)
        self._wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    # Teksten pas maken bij het tonen, zodat ze meegaan als je van taal wisselt.

    @property
    def summary(self):
        if not self._now:
            return None
        temp, code, high, low = self._now
        return tr("{temp}° · {sky} · max {high}° min {low}°", temp=temp, sky=describe_code(code),
                  high=high, low=low)

    @property
    def rain(self):
        return rain_text(self._rain) if self._rain else None

    @property
    def error(self):
        return tr(self._error) if self._error else None

    def set_place(self, place):
        if place == self.place:
            return
        self.place = place
        self._now = self._rain = self._error = None
        self._wake.set()

    def _loop(self):
        while True:
            place, delay = self.place, REFRESH_SECONDS
            if place:
                try:
                    now, rain = self._fetch(place)
                    if place == self.place:  # intussen niet van plaats gewisseld
                        self._now, self._rain, self._error = now, rain, None
                except PlaceNotFound:
                    self._error = "Plaats niet gevonden"
                    delay = None  # pas opnieuw proberen als de plaats verandert
                except Exception as err:
                    print(f"Weer ophalen mislukt: {err}", flush=True)
                    self._error = "Weer ophalen mislukt"
                    delay = RETRY_SECONDS
            self._wake.wait(delay if place else None)
            self._wake.clear()

    def _fetch(self, place):
        if not self._coords or self._coords[0] != place:
            self._coords = (place, *self._geocode(place))
        _, lat, lon = self._coords
        return self._forecast(lat, lon)

    def _geocode(self, place):
        params = {"name": place, "count": 1, "language": language()}
        if self.country:
            params["countryCode"] = self.country
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search", params=params, timeout=10)
        r.raise_for_status()
        results = r.json().get("results") or []
        if not results:
            raise PlaceNotFound(place)
        return results[0]["latitude"], results[0]["longitude"]

    def _forecast(self, lat, lon):
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=10, params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,weather_code",
            "hourly": "precipitation_probability",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto", "forecast_days": 2,
        })
        r.raise_for_status()
        data = r.json()
        cur, daily = data["current"], data["daily"]
        now = (round(cur["temperature_2m"]), cur["weather_code"],
               round(daily["temperature_2m_max"][0]), round(daily["temperature_2m_min"][0]))
        return now, rain_forecast(cur["time"], data["hourly"])
