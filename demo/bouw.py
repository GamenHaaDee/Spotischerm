"""Bouwt de browserdemo naar docs/demo/ (pygame -> WebAssembly met pygbag).

Gebruik (in een eigen venv, niet die van de Pi):
    python -m venv .demo-venv
    .demo-venv/bin/pip install pygbag segno
    .demo-venv/bin/python demo/bouw.py

Nodig: DejaVuSans.ttf en DejaVuSans-Bold.ttf, plus hun licentie. Op Linux staan de lettertypes in
/usr/share/fonts/truetype/dejavu en de licentie in /usr/share/doc/fonts-dejavu-core/copyright (pakket
fonts-dejavu-core); geef anders de map op met --fonts (de licentie mag daar als LICENSE* in staan).
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ["spotischerm", "common", "discovery", "hardware", "fonts", "i18n", "lyrics", "share", "weather"]
FONT_FILES = ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fonts", default="/usr/share/fonts/truetype/dejavu", help="map met de DejaVu-lettertypes")
    args = parser.parse_args()
    fonts = Path(args.fonts)
    missing = [f for f in FONT_FILES if not (fonts / f).exists()]
    if missing:
        sys.exit(f"Lettertypes niet gevonden in {fonts}: {', '.join(missing)}. Gebruik --fonts.")
    import segno  # zit straks in het pakket: QR-codes werken dan ook in de browser

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "spotischerm-demo"
        stage.mkdir()
        shutil.copy(ROOT / "demo" / "main.py", stage)
        for name in MODULES:
            shutil.copy(ROOT / "app" / f"{name}.py", stage)
        for name in FONT_FILES:
            shutil.copy(fonts / name, stage)
        shutil.copytree(Path(segno.__file__).parent, stage / "segno",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        subprocess.run([sys.executable, "-m", "pygbag", "--build", "--ume_block", "0",
                        "--title", "SpotiScherm demo", str(stage)], check=True)
        out = ROOT / "docs" / "demo"
        shutil.rmtree(out, ignore_errors=True)
        shutil.copytree(stage / "build" / "web", out, dirs_exist_ok=True)  # map kan bezet zijn (sync)
    page = out / "index.html"  # grijze achtergrond van pygbag -> zwart, zoals het scherm
    page.write_text(page.read_text(encoding="utf-8").replace("#7f7f7f", "#121212"), encoding="utf-8")
    # De licentie van DejaVu moet met de lettertypes mee.
    licenses = sorted(fonts.glob("LICENSE*")) or [Path("/usr/share/doc/fonts-dejavu-core/copyright")]
    if licenses[0].exists():
        shutil.copy(licenses[0], out / "LICENSE-DejaVu.txt")
    else:
        print("Let op: licentie van DejaVu niet gevonden; zet die zelf in docs/demo/LICENSE-DejaVu.txt")
    print(f"Klaar: {out}")


if __name__ == "__main__":
    main()
