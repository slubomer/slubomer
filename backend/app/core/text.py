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
