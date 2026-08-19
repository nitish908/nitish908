"""CLI helper to create/reset a dashboard user. Usage:
    python scripts/create_user.py owner@example.com 'a-strong-password' owner
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    email, password = sys.argv[1].strip().lower(), sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else "owner"

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.password_hash = hash_password(password)
            user.role = role
            print(f"Updated existing user {email}")
        else:
            db.add(User(email=email, full_name=email.split("@")[0], password_hash=hash_password(password), role=role))
            print(f"Created user {email}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
