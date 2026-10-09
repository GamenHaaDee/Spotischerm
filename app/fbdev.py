"""Rechtstreeks tekenen in /dev/fb0 en zelf touch/muis uitlezen, zonder SDL-beeld.

Voor Pi's waarop SDL via KMS/EGL geen (of zwart) beeld geeft, zoals de Pi 1. Pygame tekent
dan op een gewoon canvas (SDL "dummy"), en wij kopiëren dat naar het beeldgeheugen van de
console. Touch en muis lezen we uit /dev/input en sturen we als gewone pygame-muisevents door,
zodat de rest van de app niets merkt.
"""
import fcntl
import mmap
import os
import select
import struct
import threading
import time

import pygame

EV_SYN, EV_KEY, EV_REL, EV_ABS = 0, 1, 2, 3
ABS_X, ABS_Y, ABS_MT_X, ABS_MT_Y, ABS_MT_TRACKING_ID = 0, 1, 53, 54, 57
REL_X, REL_Y, REL_WHEEL = 0, 1, 8
BTN_LEFT, BTN_TOUCH = 272, 330
EVENT = struct.Struct("llHHi")  # struct input_event (16 bytes op 32-bit, 24 op 64-bit)
LONG_BITS = struct.calcsize("l") * 8


def _sysfs(name, key):
    with open(f"/sys/class/graphics/{name}/{key}", encoding="ascii") as f:
        return f.read().strip()


class FrameBuffer:
    def __init__(self, name="fb0"):
        self.w, self.h = map(int, _sysfs(name, "virtual_size").split(","))
        self.bpp = int(_sysfs(name, "bits_per_pixel"))
        self.stride = int(_sysfs(name, "stride"))
        if self.bpp == 16:
            masks = (0xF800, 0x07E0, 0x001F, 0)          # RGB565
        elif self.bpp == 32:
            masks = (0xFF0000, 0x00FF00, 0x0000FF, 0)    # XRGB8888
        else:
            raise RuntimeError(f"{self.bpp} bits per pixel wordt niet ondersteund")
        self.masks = masks
        self.out = pygame.Surface((self.w, self.h), 0, self.bpp, masks)
        self.file = open(f"/dev/{name}", "r+b")
        self.mem = mmap.mmap(self.file.fileno(), self.stride * self.h)
        self.unblanked = 0.0

    def unblank(self):
        """Het scherm aanzetten als de console het in slaap heeft gezet (anders zie je zwart)."""
        try:
            fcntl.ioctl(self.file, 0x4611, 0)  # FBIOBLANK, FB_BLANK_UNBLANK
        except OSError:
            pass
        self.unblanked = time.monotonic()

    def show(self, surface):
        if time.monotonic() - self.unblanked > 30:
            self.unblank()
        # Tekent de app al in hetzelfde formaat (zie open_display), dan hoeft er niks omgezet te worden.
        if surface.get_bitsize() == self.bpp and tuple(surface.get_masks()[:3]) == self.masks[:3]:
            src = surface
        else:
            self.out.blit(surface, (0, 0))
            src = self.out
        pitch = src.get_pitch()
        view = memoryview(src.get_view("0")).cast("B")  # direct uit het canvas, zonder tussenkopie
        if pitch == self.stride:
            self.mem[:pitch * self.h] = view[:pitch * self.h]
        else:
            row = self.w * self.bpp // 8
            for y in range(self.h):
                self.mem[y * self.stride:y * self.stride + row] = view[y * pitch:y * pitch + row]


def _bits(path):
    try:
        words = open(path, encoding="ascii").read().split()
    except OSError:
        return 0
    value = 0
    for word in words:
        value = (value << LONG_BITS) | int(word, 16)
    return value


def _pointer_devices():
    """Touchscreens (absolute X/Y) en muizen (relatieve X/Y)."""
    found = []
    for name in sorted(os.listdir("/dev/input")):
        if not name.startswith("event"):
            continue
        caps = f"/sys/class/input/{name}/device/capabilities"
        abs_bits, rel_bits = _bits(f"{caps}/abs"), _bits(f"{caps}/rel")
        touch = (abs_bits >> ABS_X) & (abs_bits >> ABS_Y) & 1 or (abs_bits >> ABS_MT_X) & (abs_bits >> ABS_MT_Y) & 1
        mouse = (rel_bits >> REL_X) & (rel_bits >> REL_Y) & 1
        if touch or mouse:
            found.append(f"/dev/input/{name}")
    return found


def _absinfo(fd, code):
    """(min, max) van een absolute as, via de EVIOCGABS-ioctl."""
    buf = bytearray(24)
    fcntl.ioctl(fd, 0x80184540 + code, buf)
    _, lo, hi, *_ = struct.unpack("6i", buf)
    return lo, max(hi, lo + 1)


class InputReader(threading.Thread):
    """Leest touch en muis en zet ze om in pygame-muisevents."""

    def __init__(self, width, height):
        super().__init__(daemon=True)
        self.w, self.h = width, height
        self.x, self.y = width // 2, height // 2
        self.devstate = {}

    def run(self):
        devices = {}
        last_scan = 0
        while True:
            if time.monotonic() - last_scan > 5:  # ook een later aangesloten muis of scherm vinden
                last_scan = time.monotonic()
                for path in _pointer_devices():
                    if path not in devices.values():
                        try:
                            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                        except OSError:
                            continue
                        devices[fd] = path
                        self.devstate[fd] = self._new_state(fd)
            if not devices:
                time.sleep(1)
                continue
            ready, _, _ = select.select(list(devices), [], [], 1)
            for fd in ready:
                try:
                    data = os.read(fd, EVENT.size * 64)
                except OSError:  # losgekoppeld
                    os.close(fd)
                    devices.pop(fd, None)
                    continue
                for i in range(0, len(data) - EVENT.size + 1, EVENT.size):
                    try:
                        self.on_event(fd, *EVENT.unpack_from(data, i)[2:])
                    except Exception as err:  # één vreemd event mag het lezen niet stilleggen
                        print(f"Invoer: {err}", flush=True)

    def _new_state(self, fd):
        ranges = {}
        for code in (ABS_X, ABS_Y, ABS_MT_X, ABS_MT_Y):
            try:
                ranges[code] = _absinfo(fd, code)
            except OSError:
                pass
        return {"ranges": ranges, "down": False, "press": None, "moved": False}

    # Let op: geen namen als _handle of _state; die gebruikt threading.Thread zelf (Python 3.13+).
    def on_event(self, fd, etype, code, value):
        st = self.devstate[fd]
        if etype == EV_ABS and code in st["ranges"]:
            lo, hi = st["ranges"][code]
            if code in (ABS_X, ABS_MT_X):
                self.x = int((value - lo) * (self.w - 1) / (hi - lo))
            else:
                self.y = int((value - lo) * (self.h - 1) / (hi - lo))
            st["moved"] = True
        elif etype == EV_ABS and code == ABS_MT_TRACKING_ID:
            st["press"] = value >= 0
        elif etype == EV_REL and code in (REL_X, REL_Y):
            if code == REL_X:
                self.x = max(0, min(self.w - 1, self.x + value))
            else:
                self.y = max(0, min(self.h - 1, self.y + value))
            st["moved"] = True
        elif etype == EV_REL and code == REL_WHEEL:
            pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=value, flipped=False))
        elif etype == EV_KEY and code in (BTN_TOUCH, BTN_LEFT):
            st["press"] = value == 1
        elif etype == EV_SYN and code == 0:
            pos = (self.x, self.y)
            if st["press"] is True and not st["down"]:
                st["down"] = True
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
            elif st["moved"] and st["down"]:
                pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(1, 0, 0)))
            if st["press"] is False and st["down"]:
                st["down"] = False
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))
            st["press"], st["moved"] = None, False
