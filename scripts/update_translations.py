"""Refresh the translation files: extract strings, fill Italian translations, compile.

    uv run python scripts/update_translations.py

1. ``pyside6-lupdate`` extracts the strings of ``src/photosaver/ui`` into the ``.ts`` file;
2. the Italian translations of ``translations_it.py`` are written into it;
3. ``pyside6-lrelease`` compiles the ``.qm`` file loaded at run time.

New strings without a translation are reported and the script exits with an error.
"""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from translations_en import plural_forms
from translations_it import ITALIAN

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "src" / "photosaver" / "ui"
I18N = ROOT / "src" / "photosaver" / "i18n"
TS = I18N / "photosaver_it.ts"
TS_EN = I18N / "photosaver_en.ts"


def run(*args: str) -> None:
    subprocess.run(args, check=True, cwd=ROOT, stdout=subprocess.DEVNULL)


def fill(ts: Path) -> list[str]:
    tree = ET.parse(ts)
    missing = []
    for message in tree.getroot().iter("message"):
        source = message.find("source").text or ""
        translation = message.find("translation")
        value = ITALIAN.get(source)
        if value is None:
            missing.append(source)
            continue
        translation.attrib.pop("type", None)
        if message.get("numerus") == "yes":
            for child in list(translation):
                translation.remove(child)
            translation.text = None
            for form in value if isinstance(value, tuple) else (value, value):
                ET.SubElement(translation, "numerusform").text = form
        else:
            translation.text = value
    tree.write(ts, encoding="utf-8", xml_declaration=True)
    return missing


def fill_english(ts: Path) -> None:
    """Only plural forms: other texts are already English."""
    tree = ET.parse(ts)
    for message in tree.getroot().iter("message"):
        if message.get("numerus") != "yes":
            continue
        translation = message.find("translation")
        translation.attrib.pop("type", None)
        for child in list(translation):
            translation.remove(child)
        translation.text = None
        for form in plural_forms(message.find("source").text or ""):
            ET.SubElement(translation, "numerusform").text = form
    tree.write(ts, encoding="utf-8", xml_declaration=True)


def main() -> int:
    I18N.mkdir(parents=True, exist_ok=True)
    sources = sorted(str(p.relative_to(ROOT)) for p in UI.glob("*.py"))
    run("pyside6-lupdate", *sources, "-no-obsolete", "-target-language", "it_IT", "-ts", str(TS))
    missing = fill(TS)
    run("pyside6-lrelease", str(TS), "-qm", str(TS.with_suffix(".qm")))
    run("pyside6-lupdate", *sources, "-no-obsolete", "-target-language", "en", "-ts", str(TS_EN))
    fill_english(TS_EN)
    run("pyside6-lrelease", str(TS_EN), "-qm", str(TS_EN.with_suffix(".qm")))
    if missing:
        print("Missing Italian translations:", *missing, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
