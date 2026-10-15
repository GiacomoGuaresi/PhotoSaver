"""English plural forms. Texts are written in English with "(s)" (``%n photo(s)``): Qt needs
a translation to choose singular or plural. Most are derived by :func:`plural_forms`;
the few where that is not enough are written here."""

import re

ENGLISH_OVERRIDES: dict[str, tuple[str, str]] = {
    "%n file(s) are not photos or videos: they stay where they are.": (
        "%n file is not a photo or video: it stays where it is.",
        "%n files are not photos or videos: they stay where they are.",
    ),
    "%n photo(s) are already on the disks: I won't copy them again.": (
        "%n photo is already on the disks: I won't copy it again.",
        "%n photos are already on the disks: I won't copy them again.",
    ),
    "%n photo(s) are already in your photos in another folder: I'll skip them.": (
        "%n photo is already in your photos in another folder: I'll skip it.",
        "%n photos are already in your photos in another folder: I'll skip them.",
    ),
    "%n photo(s) have the same name as different photos already there: I'll save them with "
    "a new name.": (
        "%n photo has the same name as a different photo already there: "
        "I'll save it with a new name.",
        "%n photos have the same name as different photos already there: "
        "I'll save them with a new name.",
    ),
    "%n file(s) could not be copied: they were changed or can't be read. They stay on the "
    "computer.": (
        "%n file could not be copied: it was changed or can't be read. It stays on the computer.",
        "%n files could not be copied: they were changed or can't be read. "
        "They stay on the computer.",
    ),
    "… and %n more": ("… and %n more", "… and %n more"),
    "%n photo(s) here need attention. Check the disks.": (
        "%n photo here needs attention. Check the disks.",
        "%n photos here need attention. Check the disks.",
    ),
}

_SINGULAR = [(r"\(s\)", ""), (r"\bare\b", "is"), (r"\bwere\b", "was"), (r"\bhave\b", "has")]


def plural_forms(source: str) -> tuple[str, str]:
    if source in ENGLISH_OVERRIDES:
        return ENGLISH_OVERRIDES[source]
    singular = source
    for pattern, replacement in _SINGULAR:
        singular = re.sub(pattern, replacement, singular)
    return singular, source.replace("(s)", "s")
