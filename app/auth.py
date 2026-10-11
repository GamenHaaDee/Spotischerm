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
# Het abonnement ('product') geeft Spotify sinds februari 2026 niet meer aan eigen apps.
# Komt het toch mee (bijv. bij een app met uitgebreide toegang), dan tonen we het.
product = me.get("product")
plan = f" (Spotify {product.capitalize()})" if product else ""
print(f"\nIngelogd als {me.get('display_name') or me['id']}{plan}.")

if product and product != "premium":
    print("Let op: afspelen bedienen via de Web API werkt alleen met Spotify Premium.")
elif not product:
    print("Afspelen bedienen werkt alleen met Spotify Premium (het abonnement kan de app zelf niet zien).")

devices = sp.devices().get("devices", [])
if devices:
    print("Spotify ziet nu deze apparaten:")
    for d in devices:
        print(f"  - {d['name']} ({d['type']})")
else:
    print("Nog geen apparaten zichtbaar. Open Spotify op een speaker, telefoon of pc.")
print("\nKlaar. Herstart de app met: sudo systemctl restart spotischerm")
