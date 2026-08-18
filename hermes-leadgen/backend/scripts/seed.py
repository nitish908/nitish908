"""Idempotent startup seed: bootstraps the first owner account (from
SEED_OWNER_EMAIL / SEED_OWNER_PASSWORD, if set and no users exist yet) and
the default scoring rules. Safe to run on every container start.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.scoring_engine import seed_default_scoring_rules  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        seed_default_scoring_rules(db)

        existing = db.scalar(select(User).limit(1))
        if not existing:
            email = os.environ.get("SEED_OWNER_EMAIL", "").strip().lower()
            password = os.environ.get("SEED_OWNER_PASSWORD", "")
            if email and password:
                db.add(User(email=email, full_name="Owner", password_hash=hash_password(password), role="owner"))
                print(f"Seeded initial owner account: {email}")
            else:
                print("No SEED_OWNER_EMAIL/SEED_OWNER_PASSWORD set and no users exist yet; "
                      "create one with scripts/create_user.py before logging in.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
