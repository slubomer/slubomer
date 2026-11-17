"""Run with: python -m app.seed"""

from app.core.db import SessionLocal
from app.seed import seed

if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
    print("Sample data loaded.")
