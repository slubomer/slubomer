"""Format of the promise import file (data/sluby.json).

{"meta": {...}, "sluby": [{"strana": ..., "nazov": ..., "stav": ..., "vyhodnotenie": [...]}]}

Field names stay in Slovak, the same as in the file the data team prepares.
"""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import PromiseType, VerdictValue
from app.schemas.admin import Url


class VoteIn(BaseModel):
    """Result of one vote in the National Council."""

    faza: str = Field(min_length=1, description="Napr. finalne, prve_citanie")
    vysledok: str = Field(min_length=1, description="Napr. Návrh prešiel")
    strana_za: int = Field(ge=0, description="Poslanci strany, ktorí hlasovali Za")
    clenov_strany: int = Field(ge=0, description="Počet poslancov v klube strany")
    celkom_za: int = Field(ge=0)
    pritomnych: int = Field(ge=0)


class EvidenceIn(BaseModel):
    """One item of "vyhodnotenie": a vote or a web page."""

    typ: Literal["hlasovanie", "web"]
    zdroj: Url
    datum: date | None = None
    hlasovanie: VoteIn | None = None

    @model_validator(mode="after")
    def _vote_matches_type(self) -> Self:
        if self.typ == "hlasovanie" and self.hlasovanie is None:
            raise ValueError("dôkaz typu 'hlasovanie' potrebuje pole 'hlasovanie'")
        if self.typ == "web" and self.hlasovanie is not None:
            raise ValueError("dôkaz typu 'web' nemá pole 'hlasovanie'")
        return self


class PromiseIn(BaseModel):
    """One promise. Only party, title and text are required."""

    strana: str = Field(min_length=1, max_length=200)
    nazov: str = Field(min_length=1, max_length=300)
    telo: str = Field(min_length=1)
    citacia: str | None = None  # verbatim quote from the programme
    strana_programu: int | None = Field(default=None, ge=1)
    zdroj: str | None = Field(default=None, max_length=300)  # programme title
    program_url: Url | None = None
    tema: str | None = Field(default=None, max_length=100)  # becomes the category
    typ: PromiseType | None = None
    stav: VerdictValue | None = None
    zdovodnenie: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    vyhodnotenie: list[EvidenceIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _verdict_has_reason(self) -> Self:
        if self.stav is not None and not (self.zdovodnenie or "").strip():
            raise ValueError("pri poli 'stav' treba aj 'zdovodnenie'")
        return self


class ImportMeta(BaseModel):
    """Information about how the file was made. Unknown fields are kept for the audit log."""

    model_config = ConfigDict(extra="allow")

    schema_verzia: str | None = None
    generovane_ai: bool = False  # AI Act: marks imported content and verdicts as AI-made
    aktualizovane: date | None = None


class PromiseImportFile(BaseModel):
    meta: ImportMeta = Field(default_factory=ImportMeta)
    sluby: list[PromiseIn]


class ImportResultOut(BaseModel):
    created: int = 0  # new promises
    updated: int = 0  # existing promises that got new data (fields, evidence or verdict)
    skipped: int = 0  # nothing new, or a duplicate within the file
    verdicts: int = 0  # new verdict versions (drafts for the verifier)
    evidence: int = 0  # new evidence rows
