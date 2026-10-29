"""Create (or confirm) the bootstrap super admin.

Usage:
    python -m scripts.create_super_admin
    python -m scripts.create_super_admin --email boss@ngo.org --password 'S3cure!pass' --name 'Boss'

Defaults come from SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD / SUPER_ADMIN_NAME in the environment (.env).
"""
import argparse
import sys

from app.core.security import validate_password_strength
from app.db.init_db import ensure_super_admin
from app.db.session import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument("--name")
    args = parser.parse_args()
    if args.password:
        try:
            validate_password_strength(args.password)
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1
    with SessionLocal() as db:
        user = ensure_super_admin(db, args.email, args.password, args.name)
        print(f"Super admin ready: {user.email} (id={user.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
