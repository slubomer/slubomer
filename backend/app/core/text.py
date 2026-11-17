"""Text helpers shared across the app."""

import re
import unicodedata


def normalize(text: str) -> str:
    """Lowercase and strip diacritics, so "Školstvo" and "skolstvo" compare equal."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip()


def slugify(text: str, max_length: int = 120) -> str:
    """URL-friendly id: "Štátny rozpočet" -> "statny-rozpocet"."""
    slug = re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")
    return slug[:max_length].rstrip("-")


# Letters that have their own place in the Slovak alphabet (č after c, ...).
# Other accents (á, é, ô, ...) sort like the base letter.
_SK_OWN_LETTERS = {"č": "c~", "ď": "d~", "ľ": "l~", "ň": "n~", "š": "s~", "ť": "t~", "ž": "z~"}


def sk_sort_key(text: str) -> str:
    """Sort key for Slovak alphabetical order. "ch" comes after "h"."""
    lowered = text.lower().replace("ch", "h~")
    return "".join(_SK_OWN_LETTERS.get(ch) or normalize(ch) for ch in lowered)


def unique_slug(base: str, suffix: str, taken: set[str]) -> str:
    """First free slug: base, then base-suffix, then base-suffix-2, -3, ..."""
    for candidate in (base, f"{base}-{suffix}"):
        if candidate not in taken:
            return candidate
    n = 2
    while f"{base}-{suffix}-{n}" in taken:
        n += 1
    return f"{base}-{suffix}-{n}"
