"""Volumeknop (draaiknop EC11) en bewegingssensor (PIR) op de GPIO-pinnen van de Pi.

Allebei staan standaard uit; zet ze aan in config.env (zie CONFIGURATION.md):
    SPOTISCHERM_DRAAIKNOP=1         (of eigen pinnen: A,B,drukknop, standaard 5,6,26)
    SPOTISCHERM_BEWEGING=1          (of een eigen pin, standaard 27)
Aansluiten: zie behuizing/aansluitschema-3pin.svg.

De knop en de sensor melden zich via een wachtrij; het scherm leest die in zijn eigen lus,
zodat er nooit vanuit een andere thread getekend wordt.
"""
import os
import queue

KNOB_PINS = (5, 6, 26)   # A, B, drukknop
MOTION_PIN = 27


def _pins(name, default):
    """'0'/leeg = uit, '1' = standaardpinnen, anders de pinnen zelf (komma's ertussen)."""
    value = os.environ.get(name, "").strip()
    if value in ("", "0"):
        return None
    if value == "1":
        return default
    try:
        pins = tuple(int(p) for p in value.split(","))
    except ValueError:
        print(f"{name}={value} snap ik niet; verwacht bijv. {','.join(map(str, default))}", flush=True)
        return None
    return pins if len(pins) == len(default) else None


class Hardware:
    """events: wachtrij met ("draai", +1/-1), ("druk",) en ("beweging",)."""

    def __init__(self):
        self.events = queue.Queue()
        self.knob = self.motion = False
        self.error = None
        knob_pins = _pins("SPOTISCHERM_DRAAIKNOP", KNOB_PINS)
        motion_pins = _pins("SPOTISCHERM_BEWEGING", (MOTION_PIN,))
        if not knob_pins and not motion_pins:
            return
        try:
            from gpiozero import Button, MotionSensor, RotaryEncoder
        except ImportError as err:  # op de pc, of python3-gpiozero ontbreekt
            self.error = str(err)
            print(f"Volumeknop/bewegingssensor uit: gpiozero ontbreekt ({err}). Voer install.sh opnieuw uit.",
                  flush=True)
            return
        self._parts = []  # vasthouden, anders ruimt Python ze op en stoppen ze
        try:
            if knob_pins:
                a, b, press = knob_pins
                encoder = RotaryEncoder(a, b, max_steps=0, bounce_time=0.002)
                encoder.when_rotated_clockwise = lambda: self.events.put(("draai", 1))
                encoder.when_rotated_counter_clockwise = lambda: self.events.put(("draai", -1))
                button = Button(press, pull_up=True, bounce_time=0.05)
                button.when_pressed = lambda: self.events.put(("druk",))
                self._parts += [encoder, button]
                self.knob = True
            if motion_pins:
                # pull_up=False: de pin wordt omlaag getrokken, dus zonder sensor ziet hij geen beweging
                sensor = MotionSensor(motion_pins[0], pull_up=False, queue_len=1)
                sensor.when_motion = lambda: self.events.put(("beweging",))
                self._parts.append(sensor)
                self.motion = True
        except Exception as err:  # pin bezet, geen toegang tot /dev/gpiochip, ...
            self.error = str(err)
            print(f"GPIO starten mislukt: {err}", flush=True)
