"""Vertalingen voor SpotiScherm.

De Nederlandse tekst in de code is de sleutel: tr("Terug") geeft in het Engels "Back".
Staat een tekst hier niet, dan blijft hij Nederlands. Een taal toevoegen = een blok
in TEXTS erbij, plus de naam in LANGUAGES.
"""

LANGUAGES = {"nl": "Nederlands", "en": "English", "de": "Deutsch"}
_lang = "nl"


def set_language(code):
    global _lang
    _lang = code if code in LANGUAGES else "nl"


def language():
    return _lang


def tr(text, **values):
    translated = TEXTS.get(_lang, {}).get(text, text)
    return translated.format(**values) if values else translated


def weekday(i):
    return DAYS[_lang][i]


def month(i):
    return MONTHS[_lang][i]


DAYS = {
    "nl": ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
}
MONTHS = {
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus",
           "september", "oktober", "november", "december"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
           "September", "Oktober", "November", "Dezember"],
}

TEXTS = {
    "en": {
        # algemeen en meldingen
        "{weekday} {day} {month}": "{weekday} {day} {month}",
        "‹ Terug": "‹ Back",
        "Laden…": "Loading…",
        "Menu": "Menu",
        "Geen actief apparaat, kies er een via Apparaten": "No active device, pick one under Devices",
        "Niet toegestaan (Premium nodig, of het apparaat blokkeert dit)":
            "Not allowed (Premium needed, or the device blocks this)",
        "Te veel verzoeken, even wachten": "Too many requests, please wait",
        "Spotify-fout {status}": "Spotify error {status}",
        "Geen verbinding met Spotify": "No connection to Spotify",
        "Er ging iets mis": "Something went wrong",
        "Kies eerst een apparaat": "Pick a device first",
        "In de wachtrij: {name}": "Added to queue: {name}",
        "Dit apparaat laat zich niet op afstand bedienen": "This device can't be controlled remotely",
        "Nog niet ingelogd bij Spotify": "Not logged in to Spotify yet",
        "Log in via SSH op de Pi:": "Log in via SSH on the Pi:",
        # hoofdscherm
        "Niks aan het spelen": "Nothing playing",
        "Kies een apparaat of playlist": "Pick a device or playlist",
        "Op: {name}": "On: {name}",
        "Kies apparaat": "Pick device",
        "Volume {volume}%": "Volume {volume}%",
        "Apparaten": "Devices",
        "Playlists": "Playlists",
        "Wachtrij": "Queue",
        "Timer": "Timer",
        "Timer {minutes}m": "Timer {minutes}m",
        "Slaaptimer": "Sleep timer",
        "Slaaptimer {minutes} min": "Sleep timer {minutes} min",
        "Zoeken": "Search",
        "Instellingen": "Settings",
        "Recent": "Recent",
        "+ Wachtrij": "+ Queue",
        # tijd geleden
        "{n} min geleden": "{n} min ago",
        "{n} uur geleden": "{n} h ago",
        "gisteren": "yesterday",
        "{n} dagen geleden": "{n} days ago",
        # apparaten
        "Kies een apparaat": "Pick a device",
        "Niks gevonden.\nOpen Spotify op de speaker of telefoon en tik Vernieuw.":
            "Nothing found.\nOpen Spotify on the speaker or phone and tap Refresh.",
        "Vernieuw": "Refresh",
        "Kies ‘{name}’ één keer in de Spotify-app op je telefoon. Daarna kun je hem hier bedienen.":
            "Pick ‘{name}’ once in the Spotify app on your phone. After that you can control it here.",
        "{kind} · nog niet actief bij Spotify": "{kind} · not active in Spotify yet",
        "volume {volume}%": "volume {volume}%",
        "niet te bedienen via de API": "can't be controlled via the API",
        "speelt nu": "playing now",
        "Computer": "Computer", "Telefoon": "Phone", "Tablet": "Tablet", "Speaker": "Speaker",
        "Tv": "TV", "Versterker": "Receiver", "Cast-speaker": "Cast speaker", "Chromecast": "Chromecast",
        "Spelcomputer": "Game console", "Auto": "Car", "Speakergroep": "Speaker group",
        # playlists, wachtrij, recent
        "{n} nummers": "{n} songs",
        "Geen playlists gevonden.": "No playlists found.",
        "Spotify toont alleen de nummers van playlists die van jou zijn.\n"
        "Tik op Speel alles om hem toch te starten.":
            "Spotify only shows the songs of playlists you own.\nTap Play all to start it anyway.",
        "Deze playlist is leeg.": "This playlist is empty.",
        "Speel alles": "Play all",
        "Hierna": "Up next",
        "Nu · {info}": "Now · {info}",
        "De wachtrij is leeg.\nZet nummers erin via Playlists.": "The queue is empty.\nAdd songs from Playlists.",
        "Log één keer opnieuw in bij Spotify om dit te zien: .venv/bin/python app/auth.py "
        "en herstart daarna de app.":
            "Log in to Spotify once more to see this: .venv/bin/python app/auth.py and then restart the app.",
        "Nog niks gespeeld.": "Nothing played yet.",
        # slaaptimer
        "Stopt om {time}": "Stops at {time}",
        "Wanneer stoppen?": "When to stop?",
        "De muziek stopt om {time}. De laatste minuut wordt hij zachter.":
            "The music stops at {time}. It gets quieter in the last minute.",
        "Na hoeveel minuten moet de muziek stoppen?": "After how many minutes should the music stop?",
        "{minutes} min": "{minutes} min",
        "Timer uit": "Timer off",
        "Slaaptimer: de muziek stopt over {minutes} minuten": "Sleep timer: the music stops in {minutes} minutes",
        "Slaaptimer uit": "Sleep timer off",
        "Slaaptimer: welterusten": "Sleep timer: good night",
        # zoeken en toetsenbord
        "Nummer, artiest, album…": "Song, artist, album…",
        "Zoek": "Search",
        "Annuleer": "Cancel",
        "spatie": "space",
        "Opslaan": "Save",
        "Nummer · {info}": "Song · {info}",
        "Artiest": "Artist",
        "Album · {artists}": "Album · {artists}",
        "Playlist": "Playlist",
        "Playlist · {owner}": "Playlist · {owner}",
        "Niks gevonden.\nProbeer een andere zoekterm.": "Nothing found.\nTry another search.",
        "Opnieuw": "Again",
        # instellingen
        "Weer": "Weather",
        "Rustscherm": "Idle screen",
        "Nachtmodus": "Night mode",
        "Lettertype": "Font",
        "Taal": "Language",
        "Uit": "Off",
        "na {minutes} min": "after {minutes} min",
        "nooit": "never",
        "Nooit": "Never",
        "Hoes": "Cover",
        "Klok": "Clock",
        "Zwart": "Black",
        "Rood": "Red",
        "Grijs": "Grey",
        "Weer ophalen…": "Getting weather…",
        "Plaats wijzigen": "Change place",
        "Plaats kiezen": "Pick place",
        "Geen weer": "No weather",
        "Plaats, bijv. Utrecht": "Place, e.g. Utrecht",
        "Geen weer bij de klok. Kies een plaats om het weer te zien.":
            "No weather on the clock. Pick a place to see the weather.",
        "Wat laten zien": "What to show",
        "De albumhoes groot als er muziek speelt, anders de klok.":
            "The album cover when music plays, otherwise the clock.",
        "Altijd de klok met het weer.": "Always the clock with the weather.",
        "Na hoeveel minuten": "After how many minutes",
        "Na hoeveel minuten zonder aanraken": "After how many minutes without touch",
        "geen nachtmodus": "no night mode",
        "'s avonds gedimd, 's nachts zwart": "dimmed in the evening, black at night",
        "'s avonds roder, 's nachts rode klok": "redder in the evening, red clock at night",
        "'s avonds gedimd, 's nachts donkere klok": "dimmed in the evening, dark clock at night",
        "Vanaf": "From",
        "Tot": "Until",
        "Standaard": "Default",
        "niet geïnstalleerd": "not installed",
        "Tekst ziet er zo uit": "This is how text looks",
        # kleur, scherm, info
        "Kleur": "Colour", "Groen": "Green", "Blauw": "Blue", "Oranje": "Orange", "Roze": "Pink",
        "Paars": "Purple",
        "Hoes: de kleur past zich aan elk nummer aan.": "Cover: the colour follows each song.",
        "Scherm": "Screen", "Liggend": "Landscape", "Staand (rechtsom)": "Portrait (clockwise)",
        "Staand (linksom)": "Portrait (counter-clockwise)", "Ondersteboven": "Upside down",
        "Draait het beeld en de aanraking. Staat alles op zijn kop? Kies dan de andere staande stand.":
            "Rotates the picture and the touch. Upside down? Pick the other portrait option.",
        "Info": "Info", "IP-adres": "IP address", "Naam": "Name", "Wifi": "Wi-Fi",
        "Temperatuur": "Temperature", "Draait al": "Running for", "Versie": "Version",
        "geen netwerk": "no network", "via kabel": "wired", "onbekend": "unknown",
        "goed": "good", "redelijk": "fair", "zwak": "weak",
        "verbonden": "connected", "geen verbinding": "no connection",
        "{h} uur {m} min": "{h} h {m} min", "{d} dagen {h} uur": "{d} days {h} h",
        "liggend": "landscape", "staand": "portrait", "rond": "round",
        "Songtekst": "Lyrics", "Songtekst laden…": "Loading lyrics…", "Instrumentaal": "Instrumental",
        "Geen songtekst gevonden": "No lyrics found",
        "Zuinige stand": "Economy mode", "aan": "on", "uit": "off",
        # delen
        "Delen": "Share", "Dit nummer": "This song", "Deze aflevering": "This episode",
        "Deze playlist": "This playlist", "Dit album": "This album", "Deze artiest": "This artist",
        "Deze podcast": "This podcast", "Deze lijst": "This list", "Wifi": "Wi-Fi",
        "Wachtwoord: {password}": "Password: {password}", "Geen wachtwoord": "No password",
        "QR-codes maken lukt nog niet. Voer op de Pi opnieuw bash install.sh uit en herstart de app.":
            "Can't make QR codes yet. Run bash install.sh again on the Pi and restart the app.",
        "Er speelt niks om te delen. Zet GAST_WIFI_NAAM in config.env voor een QR-code van je gast-wifi.":
            "Nothing is playing to share. Set GAST_WIFI_NAAM in config.env for a QR code of your guest Wi-Fi.",
        "Tip: zet GAST_WIFI_NAAM in config.env voor een QR-code van je gast-wifi.":
            "Tip: set GAST_WIFI_NAAM in config.env for a QR code of your guest Wi-Fi.",
        # weer
        "Helder": "Clear", "Overwegend helder": "Mostly clear", "Half bewolkt": "Partly cloudy",
        "Bewolkt": "Cloudy", "Mist": "Fog", "Motregen": "Drizzle", "Regen": "Rain",
        "IJzel": "Freezing rain", "Sneeuw": "Snow", "Regenbuien": "Showers",
        "Sneeuwbuien": "Snow showers", "Onweer": "Thunderstorm",
        "{temp}° · {sky} · max {high}° min {low}°": "{temp}° · {sky} · high {high}° low {low}°",
        "Nu kans op regen ({p}%)": "Chance of rain now ({p}%)",
        "Regen verwacht rond {time} ({p}%)": "Rain expected around {time} ({p}%)",
        "Kleine kans op regen ({p}%)": "Slight chance of rain ({p}%)",
        "Droog de komende uren": "Dry for the next few hours",
        "Plaats niet gevonden": "Place not found",
        "Weer ophalen mislukt": "Couldn't get the weather",
    },
    "de": {
        "{weekday} {day} {month}": "{weekday}, {day}. {month}",
        "‹ Terug": "‹ Zurück",
        "Laden…": "Laden…",
        "Menu": "Menü",
        "Geen actief apparaat, kies er een via Apparaten": "Kein aktives Gerät, wähle eins unter Geräte",
        "Niet toegestaan (Premium nodig, of het apparaat blokkeert dit)":
            "Nicht erlaubt (Premium nötig oder das Gerät blockiert das)",
        "Te veel verzoeken, even wachten": "Zu viele Anfragen, bitte kurz warten",
        "Spotify-fout {status}": "Spotify-Fehler {status}",
        "Geen verbinding met Spotify": "Keine Verbindung zu Spotify",
        "Er ging iets mis": "Etwas ist schiefgelaufen",
        "Kies eerst een apparaat": "Wähle zuerst ein Gerät",
        "In de wachtrij: {name}": "In der Warteschlange: {name}",
        "Dit apparaat laat zich niet op afstand bedienen": "Dieses Gerät lässt sich nicht fernsteuern",
        "Nog niet ingelogd bij Spotify": "Noch nicht bei Spotify angemeldet",
        "Log in via SSH op de Pi:": "Melde dich per SSH auf dem Pi an:",
        "Niks aan het spelen": "Es läuft nichts",
        "Kies een apparaat of playlist": "Wähle ein Gerät oder eine Playlist",
        "Op: {name}": "Auf: {name}",
        "Kies apparaat": "Gerät wählen",
        "Volume {volume}%": "Lautstärke {volume}%",
        "Apparaten": "Geräte",
        "Playlists": "Playlists",
        "Wachtrij": "Warteschlange",
        "Timer": "Timer",
        "Timer {minutes}m": "Timer {minutes}m",
        "Slaaptimer": "Schlaftimer",
        "Slaaptimer {minutes} min": "Schlaftimer {minutes} Min.",
        "Zoeken": "Suche",
        "Instellingen": "Einstellungen",
        "Recent": "Zuletzt",
        "+ Wachtrij": "+ Warteschlange",
        "{n} min geleden": "vor {n} Min.",
        "{n} uur geleden": "vor {n} Std.",
        "gisteren": "gestern",
        "{n} dagen geleden": "vor {n} Tagen",
        "Kies een apparaat": "Gerät wählen",
        "Niks gevonden.\nOpen Spotify op de speaker of telefoon en tik Vernieuw.":
            "Nichts gefunden.\nÖffne Spotify auf dem Lautsprecher oder Handy und tippe auf Aktualisieren.",
        "Vernieuw": "Aktualisieren",
        "Kies ‘{name}’ één keer in de Spotify-app op je telefoon. Daarna kun je hem hier bedienen.":
            "Wähle ‘{name}’ einmal in der Spotify-App auf deinem Handy. Danach kannst du es hier steuern.",
        "{kind} · nog niet actief bij Spotify": "{kind} · noch nicht aktiv bei Spotify",
        "volume {volume}%": "Lautstärke {volume}%",
        "niet te bedienen via de API": "nicht über die API steuerbar",
        "speelt nu": "spielt gerade",
        "Computer": "Computer", "Telefoon": "Handy", "Tablet": "Tablet", "Speaker": "Lautsprecher",
        "Tv": "TV", "Versterker": "Verstärker", "Cast-speaker": "Cast-Lautsprecher", "Chromecast": "Chromecast",
        "Spelcomputer": "Spielkonsole", "Auto": "Auto", "Speakergroep": "Lautsprechergruppe",
        "{n} nummers": "{n} Titel",
        "Geen playlists gevonden.": "Keine Playlists gefunden.",
        "Spotify toont alleen de nummers van playlists die van jou zijn.\n"
        "Tik op Speel alles om hem toch te starten.":
            "Spotify zeigt nur die Titel deiner eigenen Playlists.\n"
            "Tippe auf Alle abspielen, um sie trotzdem zu starten.",
        "Deze playlist is leeg.": "Diese Playlist ist leer.",
        "Speel alles": "Alle abspielen",
        "Hierna": "Als Nächstes",
        "Nu · {info}": "Jetzt · {info}",
        "De wachtrij is leeg.\nZet nummers erin via Playlists.":
            "Die Warteschlange ist leer.\nFüge Titel über Playlists hinzu.",
        "Log één keer opnieuw in bij Spotify om dit te zien: .venv/bin/python app/auth.py "
        "en herstart daarna de app.":
            "Melde dich einmal neu bei Spotify an, um das zu sehen: .venv/bin/python app/auth.py "
            "und starte die App danach neu.",
        "Nog niks gespeeld.": "Noch nichts gespielt.",
        "Stopt om {time}": "Stoppt um {time}",
        "Wanneer stoppen?": "Wann stoppen?",
        "De muziek stopt om {time}. De laatste minuut wordt hij zachter.":
            "Die Musik stoppt um {time}. In der letzten Minute wird sie leiser.",
        "Na hoeveel minuten moet de muziek stoppen?": "Nach wie vielen Minuten soll die Musik stoppen?",
        "{minutes} min": "{minutes} Min.",
        "Timer uit": "Timer aus",
        "Slaaptimer: de muziek stopt over {minutes} minuten": "Schlaftimer: die Musik stoppt in {minutes} Minuten",
        "Slaaptimer uit": "Schlaftimer aus",
        "Slaaptimer: welterusten": "Schlaftimer: gute Nacht",
        "Nummer, artiest, album…": "Titel, Künstler, Album…",
        "Zoek": "Suchen",
        "Annuleer": "Abbrechen",
        "spatie": "Leertaste",
        "Opslaan": "Speichern",
        "Nummer · {info}": "Titel · {info}",
        "Artiest": "Künstler",
        "Album · {artists}": "Album · {artists}",
        "Playlist": "Playlist",
        "Playlist · {owner}": "Playlist · {owner}",
        "Niks gevonden.\nProbeer een andere zoekterm.": "Nichts gefunden.\nVersuche einen anderen Suchbegriff.",
        "Opnieuw": "Neu suchen",
        "Weer": "Wetter",
        "Rustscherm": "Ruhebildschirm",
        "Nachtmodus": "Nachtmodus",
        "Lettertype": "Schriftart",
        "Taal": "Sprache",
        "Uit": "Aus",
        "na {minutes} min": "nach {minutes} Min.",
        "nooit": "nie",
        "Nooit": "Nie",
        "Hoes": "Cover",
        "Klok": "Uhr",
        "Zwart": "Schwarz",
        "Rood": "Rot",
        "Grijs": "Grau",
        "Weer ophalen…": "Wetter wird geladen…",
        "Plaats wijzigen": "Ort ändern",
        "Plaats kiezen": "Ort wählen",
        "Geen weer": "Kein Wetter",
        "Plaats, bijv. Utrecht": "Ort, z. B. Berlin",
        "Geen weer bij de klok. Kies een plaats om het weer te zien.":
            "Kein Wetter bei der Uhr. Wähle einen Ort, um das Wetter zu sehen.",
        "Wat laten zien": "Was anzeigen",
        "De albumhoes groot als er muziek speelt, anders de klok.":
            "Das Albumcover, wenn Musik läuft, sonst die Uhr.",
        "Altijd de klok met het weer.": "Immer die Uhr mit dem Wetter.",
        "Na hoeveel minuten": "Nach wie vielen Minuten",
        "Na hoeveel minuten zonder aanraken": "Nach wie vielen Minuten ohne Berührung",
        "geen nachtmodus": "kein Nachtmodus",
        "'s avonds gedimd, 's nachts zwart": "abends gedimmt, nachts schwarz",
        "'s avonds roder, 's nachts rode klok": "abends röter, nachts rote Uhr",
        "'s avonds gedimd, 's nachts donkere klok": "abends gedimmt, nachts dunkle Uhr",
        "Vanaf": "Von",
        "Tot": "Bis",
        "Standaard": "Standard",
        "niet geïnstalleerd": "nicht installiert",
        "Tekst ziet er zo uit": "So sieht Text aus",
        "Kleur": "Farbe", "Groen": "Grün", "Blauw": "Blau", "Oranje": "Orange", "Roze": "Rosa",
        "Paars": "Lila",
        "Hoes: de kleur past zich aan elk nummer aan.": "Cover: Die Farbe passt sich jedem Titel an.",
        "Scherm": "Bildschirm", "Liggend": "Quer", "Staand (rechtsom)": "Hochkant (rechtsherum)",
        "Staand (linksom)": "Hochkant (linksherum)", "Ondersteboven": "Kopfüber",
        "Draait het beeld en de aanraking. Staat alles op zijn kop? Kies dan de andere staande stand.":
            "Dreht Bild und Touch. Steht alles auf dem Kopf? Wähle die andere Hochkant-Option.",
        "Info": "Info", "IP-adres": "IP-Adresse", "Naam": "Name", "Wifi": "WLAN",
        "Temperatuur": "Temperatur", "Draait al": "Läuft seit", "Versie": "Version",
        "geen netwerk": "kein Netzwerk", "via kabel": "per Kabel", "onbekend": "unbekannt",
        "goed": "gut", "redelijk": "mittel", "zwak": "schwach",
        "verbonden": "verbunden", "geen verbinding": "keine Verbindung",
        "{h} uur {m} min": "{h} Std. {m} Min.", "{d} dagen {h} uur": "{d} Tage {h} Std.",
        "liggend": "quer", "staand": "hochkant", "rond": "rund",
        "Songtekst": "Songtext", "Songtekst laden…": "Songtext wird geladen…", "Instrumentaal": "Instrumental",
        "Geen songtekst gevonden": "Kein Songtext gefunden",
        "Zuinige stand": "Sparmodus", "aan": "an", "uit": "aus",
        "Delen": "Teilen", "Dit nummer": "Dieser Song", "Deze aflevering": "Diese Folge",
        "Deze playlist": "Diese Playlist", "Dit album": "Dieses Album", "Deze artiest": "Dieser Künstler",
        "Deze podcast": "Dieser Podcast", "Deze lijst": "Diese Liste", "Wifi": "WLAN",
        "Wachtwoord: {password}": "Passwort: {password}", "Geen wachtwoord": "Kein Passwort",
        "QR-codes maken lukt nog niet. Voer op de Pi opnieuw bash install.sh uit en herstart de app.":
            "QR-Codes gehen noch nicht. Führe auf dem Pi erneut bash install.sh aus und starte die App neu.",
        "Er speelt niks om te delen. Zet GAST_WIFI_NAAM in config.env voor een QR-code van je gast-wifi.":
            "Es läuft nichts zum Teilen. Trage GAST_WIFI_NAAM in config.env ein für einen QR-Code deines Gast-WLANs.",
        "Tip: zet GAST_WIFI_NAAM in config.env voor een QR-code van je gast-wifi.":
            "Tipp: Trage GAST_WIFI_NAAM in config.env ein für einen QR-Code deines Gast-WLANs.",
        "Helder": "Klar", "Overwegend helder": "Überwiegend klar", "Half bewolkt": "Teilweise bewölkt",
        "Bewolkt": "Bewölkt", "Mist": "Nebel", "Motregen": "Nieselregen", "Regen": "Regen",
        "IJzel": "Glatteis", "Sneeuw": "Schnee", "Regenbuien": "Regenschauer",
        "Sneeuwbuien": "Schneeschauer", "Onweer": "Gewitter",
        "{temp}° · {sky} · max {high}° min {low}°": "{temp}° · {sky} · max {high}° min {low}°",
        "Nu kans op regen ({p}%)": "Jetzt Regenrisiko ({p}%)",
        "Regen verwacht rond {time} ({p}%)": "Regen erwartet gegen {time} ({p}%)",
        "Kleine kans op regen ({p}%)": "Geringe Regenwahrscheinlichkeit ({p}%)",
        "Droog de komende uren": "Trocken in den nächsten Stunden",
        "Plaats niet gevonden": "Ort nicht gefunden",
        "Weer ophalen mislukt": "Wetter konnte nicht geladen werden",
    },
}
