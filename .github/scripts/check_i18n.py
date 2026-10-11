"""Check that every language has the same texts as English, with the same {placeholders}.

Run from the repository root: python .github/scripts/check_i18n.py
"""
import string
import sys

sys.path.insert(0, "app")
import i18n  # noqa: E402

fields = lambda text: sorted(f for _, f, _, _ in string.Formatter().parse(text) if f)
reference = i18n.TEXTS["en"]
problems = []
for code in i18n.LANGUAGES:
    if code == "nl":  # Dutch is the key itself
        continue
    texts = i18n.TEXTS.get(code, {})
    for key in sorted(set(reference) - set(texts)):
        problems.append(f"{code}: missing translation for {key!r}")
    for key in sorted(set(texts) - set(reference)):
        problems.append(f"{code}: text not in English: {key!r}")
    for key, value in texts.items():
        if fields(key) != fields(value):
            problems.append(f"{code}: placeholders differ in {key!r}: {fields(key)} vs {fields(value)}")
    if len(i18n.DAYS.get(code, [])) != 7 or len(i18n.MONTHS.get(code, [])) != 12:
        problems.append(f"{code}: DAYS or MONTHS incomplete")

print("\n".join(problems) or f"Translations OK: {', '.join(i18n.LANGUAGES)}")
sys.exit(1 if problems else 0)
