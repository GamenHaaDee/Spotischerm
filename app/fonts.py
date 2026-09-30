"""Lettertypebestanden zelf vinden, zonder fc-list.

Pygame zoekt systeemlettertypes op via fc-list en geeft dat maar 1 seconde. Op een Pi 1
duurt dat langer, en dan krijg je een noodlettertype zonder tekens als ♪ en …. Daarom
kijken we zelf in de lettertypemappen, één keer bij het opstarten.
"""
import os
import re

# Per lettertype: (gewoon, vet) als bestandsnaam zonder streepjes, spaties en extensie, op
# volgorde van voorkeur: eerst de Linux-bestanden, daarna die van Windows (om op de pc te testen).
# Gewoon en vet komen altijd uit dezelfde familie.
FILES = {
    "standaard": (("dejavusans", "dejavusansbold"), ("arial", "arialbd")),
    "roboto": (("robotoregular", "robotobold"), ("roboto", "robotobold")),
    "opensans": (("opensansregular", "opensansbold"), ("opensans", "opensansbold")),
    "lato": (("latoregular", "latobold"), ("lato", "latobold")),
    "comic": (("comicneueregular", "comicneuebold"), ("comicneue", "comicneuebold"), ("comic", "comicbd")),
    "serif": (("dejavuserif", "dejavuserifbold"), ("georgia", "georgiab")),
    "mono": (("dejavusansmono", "dejavusansmonobold"), ("consola", "consolab")),
}
FONT_DIRS = (
    "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.local/share/fonts"),
    os.path.expanduser("~/.fonts"), os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
)

_index = None


def _build_index():
    index = {}
    for folder in FONT_DIRS:
        if not os.path.isdir(folder):
            continue
        for root, _, files in os.walk(folder):
            for name in files:
                stem, ext = os.path.splitext(name)
                if ext.lower() in (".ttf", ".otf"):
                    index.setdefault(re.sub(r"[^a-z0-9]", "", stem.lower()), os.path.join(root, name))
    return index


def find(family, bold=False):
    """Pad naar het bestand, of None. Zonder vet bestand valt hij terug op het gewone."""
    global _index
    if _index is None:
        _index = _build_index()
    for regular, bold_name in FILES.get(family, FILES["standaard"]):
        if regular in _index:
            return _index[bold_name] if bold and bold_name in _index else _index[regular]
    return None
