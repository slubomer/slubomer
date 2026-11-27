"""Fixed value sets shared by models, schemas and the API."""

from enum import StrEnum

from sqlalchemy import Enum


def db_enum(enum_cls: type[StrEnum]) -> Enum:
    """Store an enum as a plain string column (works on PostgreSQL and SQLite)."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=30,
        values_callable=lambda members: [m.value for m in members],
    )


class VerdictValue(StrEnum):
    """Result of a promise check. Same strings as "stav" in the imported JSON (data/sluby.json)."""

    SPLNENE = "splnene"  # the promise was kept
    CIASTOCNE = "ciastocne"  # work started or only some parts are done
    PORUSENE = "porusene"  # the party itself made it fail (e.g. its MPs voted the bill down)
    NESPLNENE = "nesplnene"  # no evidence that anything started
    # AI only: never published, stays inside the editorial team.
    NEDOSTATOK_INFORMACII = "nedostatok_informacii"


# Values that may appear on the public web.
PUBLIC_VERDICT_VALUES = (
    VerdictValue.SPLNENE,
    VerdictValue.CIASTOCNE,
    VerdictValue.PORUSENE,
    VerdictValue.NESPLNENE,
)


class VerdictState(StrEnum):
    """Where a verdict version is in the review flow."""

    NAVRH = "navrh"  # suggested, waiting for the verifier
    VRATENY = "vrateny"  # returned by the verifier
    PUBLIKOVANY = "publikovany"  # the one shown publicly
    NAHRADENY = "nahradeny"  # older version, kept for history


class PromiseType(StrEnum):
    KONKRETNY = "konkretny"
    ZAKON = "zakon"
    STAVBA = "stavba"
    VAGNY = "vagny"


class PromiseState(StrEnum):
    NAVRH = "navrh"
    SCHVALENY = "schvaleny"
    ZAMIETNUTY = "zamietnuty"


class DocumentKind(StrEnum):
    PROGRAM = "program"
    ZAKON = "zakon"
    UZNESENIE = "uznesenie"
    ROZPOCET = "rozpocet"
    ZMLUVA = "zmluva"
    HLASOVANIE = "hlasovanie"  # a vote in the National Council (nrsr.sk)
    WEB = "web"  # news article or ministry page, only a tip, not a published document
    INE = "ine"


# Public label of a political scientist's work (comments, verified verdicts).
# Only this role makes a promise "dovysvetlený" or a verdict "overený politológom".
POLITICAL_SCIENTIST = "politológ"


class UserRole(StrEnum):
    """Editorial roles. The public web needs no login."""

    REDAKTOR = "redaktor"  # manages promises and evidence
    OVEROVATEL = "overovatel"  # political scientist, approves verdicts
    ADMIN = "admin"  # manages users, must use 2FA


class EvidenceRole(StrEnum):
    ZDROJ = "zdroj"  # where the promise was made
    PODKLAD = "podklad"  # what the verdict is based on
