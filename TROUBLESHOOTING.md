# Troubleshooting SpotiScherm

Problems we actually ran into while building and installing SpotiScherm, grouped by what you
**see**. Each entry has the symptom, how to find the cause, and the fix.

> The app itself is described in [README.md](README.md) (English) and
> [README.nl.md](README.nl.md) (Nederlands) and [README.de.md](README.de.md) (Deutsch).
> Every setting is listed in [CONFIGURATION.md](CONFIGURATION.md).

**Quick index**

- [First steps: gather information](#first-steps-gather-information)
- [The service keeps restarting](#the-service-keeps-restarting)
- [`pygame.error: EGL not initialized`](#pygameerror-egl-not-initialized)
- [The screen stays black](#the-screen-stays-black) (the big one, especially on a Pi 1)
- [The screen goes black after about 10 minutes](#the-screen-goes-black-after-about-10-minutes)
- [Warning: `Process running 'fc-list' timed-out`](#warning-process-running-fc-list-timed-out)
- [Low frame rate](#low-frame-rate)
- [Touch or mouse does nothing](#touch-or-mouse-does-nothing)
- [The service runs as root](#the-service-runs-as-root)
- [Spotify errors](#spotify-errors)
- [Speakers are grey in the device list](#speakers-are-grey-in-the-device-list)
- [Weather, lyrics and album art](#weather-lyrics-and-album-art)
- [Testing on Windows](#testing-on-windows)
- [Handy extras](#handy-extras)

---

## First steps: gather information

Almost every problem starts with one of these three commands.

```bash
systemctl status spotischerm           # running? how often restarted?
journalctl -u spotischerm -n 50 --no-pager   # last log lines, including Python errors
journalctl -u spotischerm -f                 # follow the log live (Ctrl+C to stop)
```

Run the app by hand to see errors immediately. Stop the service first so they don't fight
over the screen:

```bash
sudo systemctl stop spotischerm
cd ~/spotify-scherm && SDL_VIDEODRIVER=kmsdrm .venv/bin/python app/spotischerm.py
```

On a Pi 1, just loading the app takes 10–15 seconds, so give it time before you conclude
it hangs. Turn on the FPS meter to see how fast it runs:

```bash
# in config.env
SPOTISCHERM_TOON_FPS=1
```

The **Info** page in the app (Settings → Info) shows the IP address, Wi-Fi strength,
temperature, whether Spotify is connected, the screen size and whether economy mode is on.

---

## The service keeps restarting

**Symptom:** `systemctl status` shows `Scheduled restart job, restart counter is at 11` (or
another number that keeps growing), and the process is only a few seconds old.

**Cause:** the app crashes on startup and systemd starts it again every 5 seconds.

**Fix:** find the actual error with `journalctl -u spotischerm -n 50 --no-pager`, or run it by
hand (see above). The traceback at the bottom tells you which of the sections below applies.
Common ones:

| Error | Section |
|---|---|
| `pygame.error: EGL not initialized` | [EGL not initialized](#pygameerror-egl-not-initialized) |
| `Vul dit in config.env in: SPOTIFY_CLIENT_ID` | Fill in `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `config.env` |
| `PermissionError` on `instellingen.json` or `.spotify-cache` | [The service runs as root](#the-service-runs-as-root) |
| `kmsdrm not available` / `No available video device` | [The screen stays black](#the-screen-stays-black) |

---

## `pygame.error: EGL not initialized`

**Symptom:** crash right after `Hello from the pygame community`:

```
File ".../spotischerm.py", line ..., in open_display
    surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.error: EGL not initialized
```

**Cause:** SDL (under pygame) draws without a desktop through KMS and EGL/GLES from Mesa.
**Raspberry Pi OS Lite doesn't always ship those libraries.**

**Fix:**

```bash
sudo apt install -y libegl1 libegl-mesa0 libgles2 libgbm1 libgl1-mesa-dri
sudo reboot
```

Also check that the KMS graphics driver is enabled (the line must not start with `#`):

```bash
grep -n "vc4-kms" /boot/firmware/config.txt      # expect: dtoverlay=vc4-kms-v3d
```

Current versions of `install.sh` install these packages for you.

---

## The screen stays black

**Symptom:** `systemctl status spotischerm` says `active (running)`, no errors in the log, but
you see nothing of the app.

There are three different causes. The two tests below tell you which one it is. Stop the app
before testing: `sudo systemctl stop spotischerm`.

**Test A: can SDL show anything at all?** This should turn the screen red, green and blue for
4 seconds each:

```bash
cd ~/spotify-scherm && SDL_VIDEODRIVER=kmsdrm .venv/bin/python -c "import pygame,time; pygame.display.init(); s=pygame.display.set_mode((0,0),pygame.FULLSCREEN); print(s.get_size(), pygame.display.get_driver()); [(s.fill(c), pygame.display.flip(), time.sleep(4)) for c in ((255,0,0),(0,255,0),(0,0,255))]"
```

**Test B: does writing straight to the console framebuffer show up?** This turns the screen
red for 6 seconds, bypassing SDL entirely (works for 16- and 32-bit framebuffers):

```bash
python3 - <<'EOF'
import time
w, h = map(int, open("/sys/class/graphics/fb0/virtual_size").read().split(","))
bpp = int(open("/sys/class/graphics/fb0/bits_per_pixel").read())
stride = int(open("/sys/class/graphics/fb0/stride").read())
px = b"\x00\x00\xff\x00" if bpp == 32 else b"\x00\xf8"
row = px * w + b"\x00" * (stride - w * len(px))
with open("/dev/fb0", "r+b") as fb:
    old = fb.read(stride * h); fb.seek(0); fb.write(row * h); fb.flush()
    time.sleep(6); fb.seek(0); fb.write(old)
EOF
```

| You see… | Cause | Go to |
|---|---|---|
| Nothing at all, not even the boot messages or login prompt | Resolution too high for the HDMI output | [Cause 1](#cause-1-the-resolution-is-too-high) |
| The console, but test A stays black and test B turns red | SDL/KMS doesn't reach the screen | [Cause 2](#cause-2-sdlkms-draws-but-nothing-reaches-the-screen) |
| Test A shows colours, but the app doesn't | Something in the app or its settings | Check the log; try `DRAAIEN=0` and `SCHERM_VORM=auto` |

### Cause 1: the resolution is too high

Seen on a **Pi 1 Model B** with a 1920×1200 monitor. The Pi picked 1920×1200 @ 60 Hz with a
154 MHz pixel clock, right at the limit of the Pi 1's HDMI output. The monitor showed no
picture, only the rainbow square at boot.

Check which mode is used and which modes the monitor offers:

```bash
for c in /sys/class/drm/card*-*; do echo "$c: $(cat $c/status)"; done
cat /sys/class/drm/card0-HDMI-A-1/modes | sort -u
sudo cat /sys/kernel/debug/dri/0/state | grep 'mode: "[0-9]'   # the mode in use, with pixel clock
```

**Fix:** force a lighter mode from that list, preferably with the same aspect ratio as the
monitor. Add it at the **start of the single line** in `/boot/firmware/cmdline.txt`:

```bash
sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.bak
sudo sed -i '1s|^|video=HDMI-A-1:1440x900@60 |' /boot/firmware/cmdline.txt
sudo reboot
```

If you lose the picture completely, put the SD card in a PC and remove the `video=...` part
again (or copy `cmdline.txt.bak` back). A lower resolution also makes the app much faster on
old Pis, see [Low frame rate](#low-frame-rate).

### Cause 2: SDL/KMS draws, but nothing reaches the screen

Also seen on the **Pi 1**: even with a working mode, the picture SDL makes through KMS and the
GPU stayed black, while test B (writing to `/dev/fb0` directly) worked.

**Fix:** use the **framebuffer backend**. The app then draws on an ordinary canvas, copies it
straight into `/dev/fb0` and reads touch and mouse from `/dev/input` itself. SDL is only used
for drawing, not for the screen.

```bash
# in config.env
SPOTISCHERM_FRAMEBUFFER=1
SPOTISCHERM_ZUINIG=1      # recommended on slow Pis, see below
```

```bash
sudo systemctl restart spotischerm
```

You can check what the app is drawing, even without looking at the screen, by grabbing the
framebuffer (16-bit example; this saves a raw dump you can convert on a PC):

```bash
head -c $(( $(cut -d, -f1 /sys/class/graphics/fb0/virtual_size) * $(cut -d, -f2 /sys/class/graphics/fb0/virtual_size) * $(cat /sys/class/graphics/fb0/bits_per_pixel) / 8 )) /dev/fb0 > /tmp/screen.raw
```

This is how we found out the app was drawing fine while the screen was black for another
reason (see the next section).

---

## The screen goes black after about 10 minutes

**Symptom:** the app worked, then the screen went black. The log is fine and the app keeps
running.

**Cause:** the console put the display to sleep. You can see it here (`0` = on, `4` = off):

```bash
cat /sys/class/graphics/fb0/blank
```

Writing to the framebuffer does **not** wake it up again.

**Fix:** in framebuffer mode (`SPOTISCHERM_FRAMEBUFFER=1`) the app wakes the display itself
every 30 seconds. To wake it by hand:

```bash
python3 -c "import fcntl; fcntl.ioctl(open('/dev/fb0','r+b'), 0x4611, 0)"   # FBIOBLANK, unblank
```

---

## Warning: `Process running 'fc-list' timed-out`

**Symptom:** in the log:

```
pygame/sysfont.py:226: UserWarning: Process running 'fc-list' timed-out! System fonts cannot be loaded on your platform
```

and the app shows a fallback font without characters like ♪, ‹ and …, while every font in
Settings → Font says "not installed".

**Cause:** pygame looks fonts up with `fc-list` and gives it only 1 second. On a Pi 1 the first
run takes longer, because it has to build the font cache.

**Fix:** current versions of the app don't use `fc-list` anymore. `app/fonts.py` looks up the
font files in `/usr/share/fonts` directly, which takes a few milliseconds. If fonts are still
missing, install them:

```bash
sudo apt install -y fonts-dejavu-core fonts-roboto fonts-open-sans fonts-lato fonts-comic-neue
```

---

## Low frame rate

**Symptom:** the FPS meter shows 2–4 fps and taps feel slow.

First: on the idle screen (clock or album cover) the app **deliberately** draws only 2 frames
per second. Look at the FPS while you touch the screen.

Measured on a **Pi 1 Model B** in framebuffer mode with economy mode on:

| Resolution | Time per frame | Max fps |
|---|---|---|
| 1440×900 | ~230 ms | ~4 |
| 800×600 | ~95 ms | ~10 |

For comparison, the same app on a desktop PC takes 0.3–2 ms per frame. A Pi 3B is roughly
3–4× faster than a Pi 1.

**What helps, in order of effect:**

1. **A lower resolution.** The number of pixels matters most. See
   [Cause 1](#cause-1-the-resolution-is-too-high) for how to set it. A 7" 800×480 panel is
   ideal for old Pis.
2. **Economy mode** (`SPOTISCHERM_ZUINIG=1`): a 300 px album cover instead of 640 px, plain
   instead of smooth scaling, at most 10 fps, no scrolling titles, and no coloured background
   from the cover.
3. **Framebuffer mode** on a Pi 1 is necessary anyway (see above). The app then draws directly
   in the framebuffer's pixel format (for example RGB565), so showing a frame is a plain copy
   without conversion. That saved about 140 ms per frame at 1440×900.
4. **A faster Pi.** A Pi 3B has built-in Wi-Fi as a bonus.

---

## Touch or mouse does nothing

**In normal (SDL) mode:** check that the touchscreen shows up and sends events:

```bash
sudo apt install -y evtest && sudo evtest
```

**In framebuffer mode** the app reads `/dev/input/event*` itself. It picks devices that report
absolute X/Y (touchscreens) or relative X/Y (mice), and checks for new devices every 5 seconds.
The user running the service must be in the `input` group:

```bash
id    # should include input and video
sudo usermod -aG input,video "$USER"   # then log out/in or reboot
```

A mouse works in framebuffer mode, but no cursor is drawn.

---

## The service runs as root

**Symptom:** `ps -o user -p $(systemctl show -p MainPID --value spotischerm)` says `root`,
`/etc/systemd/system/spotischerm.service` contains `User=root`, and parts of the project folder
(such as `.venv`) belong to root.

**Cause:** `install.sh` was run as root, or with `sudo`. It fills in the current user in the
service file. Current versions refuse to run as root.

**Fix:**

```bash
sudo chown -R "$USER:$USER" ~/spotify-scherm
sudo sed -i "s/^User=root/User=$USER/" /etc/systemd/system/spotischerm.service
sudo systemctl daemon-reload && sudo systemctl restart spotischerm
```

**Optional:** let your user start, stop and restart the app without a password, and nothing
else. This is handy while testing over SSH:

```bash
echo "$USER ALL=(root) NOPASSWD: /usr/bin/systemctl start spotischerm, /usr/bin/systemctl stop spotischerm, /usr/bin/systemctl restart spotischerm" | sudo tee /etc/sudoers.d/spotischerm
```

---

## Spotify errors

| Message in the app or log | Cause | Fix |
|---|---|---|
| "Niet toegestaan (Premium nodig…)" / HTTP 403 | Controlling playback through the Web API needs Spotify **Premium**. Since February 2026, apps in Development Mode also need the app **owner** to have Premium | Use a Premium account |
| "Geen actief apparaat" / HTTP 404 | Nothing is playing anywhere, so there's no device to send commands to | Pick a device under Devices, or start Spotify somewhere |
| `Insufficient client scope` on search | The search used `market=from_token`, which needs an extra permission | Fixed in the app: it searches without `market` (Spotify uses your account's country anyway) |
| "Recent" says you need to log in again | The recently-played list needs the `user-read-recently-played` scope, which older logins don't have | Run `.venv/bin/python app/auth.py` once and restart the app. Everything else keeps working until then |
| Asked to log in again after months | The refresh token expired | Run `app/auth.py` again |

About the login: the page after "Agree" redirects to `http://127.0.0.1:8888/callback?code=…`
and shows an error. **That's expected.** Copy the whole address bar back into the terminal.
You can also copy `.spotify-cache` from a PC where you already logged in.

---

## Speakers are grey in the device list

**Symptom:** Google Cast speakers (Nest, Chromecast, TVs, speaker groups) are listed but grey,
with "not active in Spotify yet".

**Cause:** the Spotify **Web API only knows Cast devices while Spotify is running on them**,
and forgets them a few minutes after playback stops. The Spotify app on your phone finds them
by itself on the local network, which the Web API can't do. SpotiScherm finds them with mDNS,
so it can at least show them.

**Fix:** pick the speaker once in the Spotify app on your phone. The list refreshes every
5 seconds, and the speaker becomes usable on the screen. There's no official way to wake a
Cast speaker through the Web API. Speakers that are always registered with Spotify, such as
Sonos, Spotify Connect speakers or a Pi running
[raspotify](https://dtcooper.github.io/raspotify/), don't have this problem.

No grey speakers at all? The Pi must be on the same network as the speakers (not a guest
network), and `python3-zeroconf` must be installed.

---

## Weather, lyrics and album art

- **Weather says "Plaats niet gevonden" (place not found):** the place is looked up with
  [Open-Meteo](https://open-meteo.com) geocoding, limited to the country in `WEER_LAND`
  (default `NL`). Check the spelling, or set `WEER_LAND` empty to search worldwide.
- **"Geen songtekst gevonden" (no lyrics found):** lyrics come from [LRCLIB](https://lrclib.net).
  The app first asks for the exact track, then searches with a cleaned-up title (without
  "- Remastered" etc.) and a similar duration. Not every song is in LRCLIB.
- **Album art looks pixelated:** normally the app uses Spotify's largest cover (640 px). In
  economy mode it's 300 px on purpose. On very large screens even 640 px gets scaled up;
  Spotify doesn't offer larger images.

---

## Testing on Windows

- **`pip install pygame` fails on a new Python (such as 3.14):** there's no wheel for it yet.
  Use `pip install pygame-ce spotipy zeroconf` instead. It's a drop-in replacement, and the
  code runs on it unchanged.
- **`install.sh` on the Pi says `$'\r': command not found`:** the file got Windows line
  endings. Fix with `sed -i 's/\r$//' install.sh`.
- **The window is shown full screen without a cursor:** set `SPOTISCHERM_WINDOWED=1` for an
  800×480 window, or `SPOTISCHERM_MUIS=1` for a cursor in full screen.
- **A round screen on a PC:** `SCHERM_VORM=rond` with `SPOTISCHERM_WINDOWED=1` gives a 540×540
  window with black corners, like the real round display.

---

## Handy extras

**SSH without typing a password.** If your normal SSH key has a passphrase, scripts and tools
can't use it unattended. A separate key without a passphrase, just for the Pi:

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/spotischerm
cat ~/.ssh/spotischerm.pub | ssh user@spotischerm.local "cat >> ~/.ssh/authorized_keys"
ssh -i ~/.ssh/spotischerm user@spotischerm.local
```

On Windows PowerShell, use `type $env:USERPROFILE\.ssh\spotischerm.pub | ssh ...` for the
second line.

**Update only the code, keep your settings and login:**

```bash
scp -r spotify-scherm/app user@spotischerm.local:~/spotify-scherm/
ssh user@spotischerm.local "sudo systemctl restart spotischerm"
```

**Tested setups**

| Pi | Screen | Settings needed |
|---|---|---|
| PC (Windows 11) | window / full screen | `SPOTISCHERM_WINDOWED=1` or `SPOTISCHERM_MUIS=1` |
| Pi 1 Model B, Raspberry Pi OS Lite 32-bit (Trixie) | 1920×1200 HDMI monitor | `video=HDMI-A-1:1440x900@60`, `SPOTISCHERM_FRAMEBUFFER=1`, `SPOTISCHERM_ZUINIG=1` |

If you get it running on other hardware, a note about what you needed is very welcome.
