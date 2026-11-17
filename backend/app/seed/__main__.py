"""Run with: python -m app.seed            (all sample data from the prototype)
or: python -m app.seed glossary   (glossary terms only)
"""

import sys

from app.core.db import SessionLocal
from app.seed import seed, seed_glossary

if __name__ == "__main__":
    glossary_only = sys.argv[1:] == ["glossary"]
    with SessionLocal() as session:
        if glossary_only:
            seed_glossary(session)
        else:
            seed(session)
    print("Glossary loaded." if glossary_only else "Sample data loaded.")
