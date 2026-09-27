"""Run from backend/: python scripts/seed_demo.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import init_db  # noqa: E402
from models.base import SessionLocal  # noqa: E402
from services.demo_seed import seed_demo  # noqa: E402


def main() -> None:
    init_db()
    with SessionLocal() as db:
        seed_demo(db)
    print("Demo roles, permissions, users, and GitHub connector are ready.")


if __name__ == "__main__":
    main()
