#!/usr/bin/env python3
"""Eenmalig inloggen bij Spotify. Draai dit via SSH op de Pi.

Het toont een link. Open die op je pc of telefoon, log in en klik
op 'Akkoord'. Je browser gaat daarna naar http://127.0.0.1:8888/callback?code=...
en geeft een foutmelding: dat hoort zo. Kopieer die hele adresbalk en plak
hem hier terug.
"""
from common import make_client

print(__doc__)
sp = make_client()
me = sp.current_user()
print(f"\nIngelogd als {me.get('display_name') or me['id']} ({me.get('product', '?')}).")

if me.get("product") != "premium":
    print("Let op: afspelen bedienen via de Web API werkt alleen met Spotify Premium.")

devices = sp.devices().get("devices", [])
if devices:
    print("Spotify ziet nu deze apparaten:")
    for d in devices:
        print(f"  - {d['name']} ({d['type']})")
else:
    print("Nog geen apparaten zichtbaar. Open Spotify op een speaker, telefoon of pc.")
print("\nKlaar. Herstart de app met: sudo systemctl restart spotischerm")
