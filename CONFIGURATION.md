# Configuration

Every setting SpotiScherm has, in one place.

> Also available: [README.md](README.md) (English) · [README.nl.md](README.nl.md) (Nederlands) ·
> [README.de.md](README.de.md) (Deutsch) · [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Where settings live

| File | What's in it | Who writes it |
|---|---|---|
| `config.env` | Your Spotify keys, the hardware settings and the **defaults** for everything else | you, with a text editor (`nano config.env`) |
| `instellingen.json` | What you choose on the screen (gear icon) | the app, as soon as you change something |
| `.spotify-cache` | Your Spotify login | `app/auth.py` |

**Screen settings win.** Anything set in `instellingen.json` takes priority over the same setting
in `config.env`. So if you change the weather location in `config.env` but chose another one on
the screen earlier, the screen choice stays. Delete `instellingen.json` to go back to the
`config.env` defaults.

After editing `config.env`, restart the app: `sudo systemctl restart spotischerm`. Screen settings
take effect immediately.

The names are Dutch because the project started in Dutch: *zuinig* = economy, *scherm* = screen,
*weer* = weather, *nacht* = night, *rust* = rest/idle, *draaien* = rotate, *kleur* = colour,
*taal* = language, *lettertype* = font, *gast* = guest, *wachtwoord* = password, *beveiliging* = security.

---

## `config.env`

Start from [config.example.env](config.example.env). `install.sh` copies it to `config.env` for
you. Lines starting with `#` are comments. `1` means on, `0` means off.

### Spotify (required)

| Setting | Default | Meaning |
|---|---|---|
| `SPOTIFY_CLIENT_ID` | — | **Required.** Client ID of your own app on the [Spotify developer dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | — | **Required.** Client Secret of that app. Keep it private; `config.env` is in `.gitignore` |
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:8888/callback` | Must match the Redirect URI of your Spotify app **exactly**. You normally don't change it |

### Defaults for the screen settings

You can also change these on the screen. See the [mapping table](#instellingenjson) below.

| Setting | Default | Values | Meaning |
|---|---|---|---|
| `WEER_PLAATS` | *(empty)* | a place name, e.g. `Utrecht` | Location for the weather on the clock. Empty = no weather |
| `WEER_LAND` | `NL` | two-letter country code, or empty | Country to look the place up in ([Open-Meteo](https://open-meteo.com) geocoding). Empty = search worldwide |
| `RUST_SCHERM` | `hoes` | `hoes`, `klok` | Idle screen: `hoes` = the album cover when music plays (the clock otherwise), `klok` = always the clock |
| `SPOTISCHERM_IDLE_MIN` | `5` | minutes; `0` = never | Minutes without touch before the idle screen appears (also while music plays) |
| `NACHT_STIJL` | `rood` | `uit`, `zwart`, `rood`, `grijs` | Night mode: off, black screen, dim red clock, or dim grey clock |
| `NACHT_VAN` | `23:00` | `HH:MM` | Start of the night. Leave `NACHT_VAN` and `NACHT_TOT` both empty to turn night mode off |
| `NACHT_TOT` | `07:00` | `HH:MM` | End of the night |
| `TAAL` | `nl` | `nl`, `en`, `de`, `fr`, `es` | Language of the app |
| `LETTERTYPE` | `standaard` | `standaard`, `roboto`, `opensans`, `lato`, `comic`, `serif`, `mono` | Font. `install.sh` installs them all on the Pi |
| `KLEUR` | `groen` | `groen`, `blauw`, `oranje`, `roze`, `paars`, `hoes` | Accent colour for buttons and bars. `hoes` = taken from the album cover of each song |
| `GAST_WIFI_NAAM` | *(empty)* | network name | Guest Wi-Fi for the Share page: guests scan the QR code and join. Empty = no Wi-Fi QR code |
| `GAST_WIFI_WACHTWOORD` | *(empty)* | password | Password of that network. **It is shown readable on the screen**, so preferably use a separate guest network. Empty = open network |
| `GAST_WIFI_BEVEILIGING` | `WPA` | `WPA`, `WEP`, `geen` | Security type. `WPA` also covers WPA2 and WPA3 |
| `DRAAIEN` | `0` | `0`, `90`, `270`, `180` | Rotate the picture (and touch) clockwise: 0 = landscape, 90/270 = portrait, 180 = upside down |

### Hardware and screen

| Setting | Default | Values | Meaning |
|---|---|---|---|
| `SCHERM_VORM` | `auto` | `auto`, `rond`, `rechthoek` | Layout. `auto` picks the round layout for a (nearly) square screen. Portrait comes from `DRAAIEN` |
| `SPOTISCHERM_FRAMEBUFFER` | `0` | `0`, `1` | `1` = draw straight into `/dev/fb0` instead of through SDL/KMS, and read touch and mouse input from `/dev/input` directly. Needed on the Pi 1, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#the-screen-stays-black) |
| `SPOTISCHERM_ZUINIG` | `0` | `0`, `1` | Economy mode for slow Pis: 300 px album cover, simple scaling, at most 10 fps, no scrolling titles, no coloured background |
| `SPOTISCHERM_WINDOWED` | `0` | `0`, `1` | `1` = run in an 800×480 window (540×540 when round), for testing on a PC |
| `SPOTISCHERM_MUIS` | `0` | `0`, `1` | `1` = show the mouse cursor in full screen. Not available in framebuffer mode |
| `SPOTISCHERM_TOON_FPS` | `0` | `0`, `1` | `1` = show frames per second and milliseconds per frame in the top right |
| `SPOTISCHERM_VERZOEKJES` | `1` | `0`, `1` | `1` = guests on your Wi-Fi can add songs to the queue via `http://spotischerm.local:8080/verzoekjes` (max 3 per guest per 15 min). Needs the web page (`SPOTISCHERM_WEB_POORT`) |
| `SPOTISCHERM_UPDATES` | `1` | `0`, `1` | `1` = check GitHub every 6 hours for a new version, and allow updating from Settings → Update. `0` = never contact GitHub |
| `SPOTISCHERM_WEB_POORT` | `8080` | a port number, or `0` | Port of the settings page for your phone (`http://spotischerm.local:8080`). `0` = off. Ports below 1024 don't work, the app doesn't run as root |

### Set by the service

These are set in `spotischerm.service`, not in `config.env`:

| Variable | Value | Meaning |
|---|---|---|
| `SDL_VIDEODRIVER` | `kmsdrm` | Draw without a desktop. In framebuffer mode the app switches to `dummy` by itself |
| `PYTHONUNBUFFERED` | `1` | Log lines show up in `journalctl` immediately |

---

## `instellingen.json`

The screen settings (gear icon) and the key each one is saved under:

| On the screen | Key in `instellingen.json` | Same as in `config.env` |
|---|---|---|
| Weather → place | `weer_plaats` | `WEER_PLAATS` |
| Idle screen → what to show | `rust_scherm` | `RUST_SCHERM` |
| Idle screen → after how many minutes | `idle_min` (`0` = never) | `SPOTISCHERM_IDLE_MIN` |
| Night mode → style | `nacht_stijl` | `NACHT_STIJL` |
| Night mode → from / until | `nacht_van`, `nacht_tot` | `NACHT_VAN`, `NACHT_TOT` |
| Font | `lettertype` | `LETTERTYPE` |
| Colour | `kleur` | `KLEUR` |
| Language | `taal` | `TAAL` |
| Screen (rotation) | `draaien` | `DRAAIEN` |

An example:

```json
{
  "weer_plaats": "Utrecht",
  "idle_min": 5,
  "nacht_stijl": "rood",
  "nacht_van": "23:00",
  "nacht_tot": "07:00",
  "rust_scherm": "hoes",
  "taal": "en",
  "lettertype": "standaard",
  "kleur": "hoes",
  "draaien": 0
}
```

For the settings with a fixed list of choices (night style, idle screen, language, font, colour,
rotation), an unknown value falls back to the default. An old `nacht_aan: true/false` from an
earlier version is converted to `nacht_stijl` automatically.

---

## Fixed values in the code

For tinkering. These are constants at the top of [app/spotischerm.py](app/spotischerm.py); change
them there and restart the app.

| Constant | Value | Meaning |
|---|---|---|
| `FPS` | `24` | Frames per second while you touch the screen |
| `CALM_FPS` | `5` | Frames per second when nobody touches the screen (the clock and black night screen use 2) |
| `MARQUEE_FPS` | `24` | Frames per second while a long title scrolls |
| `ECONOMY_FPS` | `(10, 2)` | Frames per second in economy mode: (touching, idle) |
| `POLL_SECONDS` | `2.0` | How often the app asks Spotify what's playing |
| `DEVICES_REFRESH` | `5` | Seconds between refreshes of the open device list |
| `MARQUEE_PAUSE`, `MARQUEE_SPEED` | `3.0`, `40` | Seconds a long title waits before scrolling, and how fast it scrolls |
| `SLEEP_OPTIONS` | `15 … 120` | The minutes you can pick for the sleep timer |
| `FADE_SECONDS` | `60` | Sleep timer: seconds over which the volume fades out |
| `IDLE_OPTIONS` | `1 … 60, 0` | The minutes you can pick for the idle screen (`0` = never) |
| `NIGHT_AWAKE_SECONDS` | `30` | At night: seconds the screen stays on after a tap |
| `EVENING_FADE`, `MORNING_FADE` | `60`, `30` | Minutes of gradual dimming before the night and brightening after it |
| `NIGHT_STEP` | `30` | Minutes per tap on the − / + of the night times |
| `INFO_REFRESH` | `5` | Seconds between refreshes of IP, Wi-Fi and temperature on the info page |

The weather refreshes every 15 minutes (`REFRESH_SECONDS` in [app/weather.py](app/weather.py)).
Adding a language is described in the README.
