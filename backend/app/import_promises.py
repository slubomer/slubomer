"""Import promises from a JSON file on the command line.

The format is described in app/schemas/promise_import.py, the import itself in
app/services/promise_import_service.py (the editorial API uses the same service).
An invalid file prints its errors and nothing is saved.

Usage (in backend/): python -m app.import_promises ../data/sluby.json
"""

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.core.db import SessionLocal
from app.schemas.promise_import import PromiseImportFile
from app.services.promise_import_service import import_file


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m app.import_promises <path/to/sluby.json>")
    path = Path(sys.argv[1])
    try:
        data = PromiseImportFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except ValidationError as error:
        sys.exit(f"Invalid file {path.name}, nothing was imported:\n{error}")

    with SessionLocal() as db:
        result = import_file(db, data, source=path.name)
    print(
        f"Promises created: {result.created}, updated: {result.updated}, "
        f"skipped: {result.skipped}, verdict drafts: {result.verdicts}, "
        f"evidence: {result.evidence}"
    )


if __name__ == "__main__":
    main()
