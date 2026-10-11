#!/usr/bin/env bash
# Installeert SpotiScherm op Raspberry Pi OS Lite. Draai als je normale gebruiker:
#   cd ~/spotify-scherm && bash install.sh
set -euo pipefail
cd "$(dirname "$0")"

# Als root (of met sudo) zou de service als root gaan draaien en worden de bestanden van root.
if [ "$(id -u)" -eq 0 ]; then
  echo "Voer dit uit als je gewone gebruiker, zonder sudo: bash install.sh" >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y python3-pygame python3-requests python3-venv python3-zeroconf \
  fonts-dejavu-core fonts-roboto fonts-open-sans fonts-lato fonts-comic-neue
# Grafische onderdelen (EGL/GLES van Mesa) die SDL nodig heeft om zonder desktop op het
# scherm te tekenen. Op Raspberry Pi OS Lite ontbreken ze soms ("EGL not initialized").
sudo apt-get install -y libegl1 libegl-mesa0 libgles2 libgbm1 libgl1-mesa-dri

python3 -m venv --system-site-packages .venv
.venv/bin/pip install --upgrade spotipy segno

# Toegang tot scherm en touchscreen zonder desktop
sudo usermod -aG video,input,render "$USER"

# Zonder wachtwoord: de Pi uitzetten of herstarten (knoppen onder Instellingen > Aan/uit) en de
# app zelf stoppen/starten. Verder niets. Eerst controleren met visudo, zodat sudo nooit stukgaat.
rule=$(mktemp)
echo "$USER ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff, /usr/bin/systemctl reboot, /usr/bin/systemctl stop spotischerm, /usr/bin/systemctl start spotischerm, /usr/bin/systemctl restart spotischerm" > "$rule"
if sudo visudo -cqf "$rule"; then
  sudo install -m 440 -o root -g root "$rule" /etc/sudoers.d/spotischerm
else
  echo "Let op: sudo-regel voor Aan/uit niet geplaatst" >&2
fi
rm -f "$rule"

[ -f config.env ] || cp config.example.env config.env

sed "s|__USER__|$USER|g; s|__DIR__|$PWD|g" spotischerm.service \
  | sudo tee /etc/systemd/system/spotischerm.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable spotischerm

cat <<EOF

Geinstalleerd. Nog drie stappen:
  1. nano config.env                  (Client ID en Secret invullen)
  2. .venv/bin/python app/auth.py     (eenmalig inloggen bij Spotify)
  3. sudo reboot
EOF
