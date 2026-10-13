"""Assign an existing account role using the backend environment, without an HTTP API."""

import argparse
import asyncio
import getpass
import os

from sqlalchemy.exc import SQLAlchemyError

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.db.session import dispose_db
from hippobox.platform.models import api_key  # noqa: F401 - register User.api_keys in standalone CLI processes
from hippobox.platform.models.user import UserRole, Users


async def change_role(email: str, role: UserRole) -> tuple[int, str, str]:
    if not SETTINGS.LOGIN_ENABLED:
        raise ValueError(
            "Role management requires LOGIN_ENABLED=true; disabled login uses a bootstrap admin."
        )
    return await Users.set_operator_role(
        email.strip().lower(), role, operator=f"cli:{getpass.getuser()}"
    )


async def _run(email: str, role: UserRole) -> tuple[int, str, str]:
    try:
        return await change_role(email, role)
    finally:
        await dispose_db()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=os.environ.get("EMAIL"))
    parser.add_argument(
        "--role", choices=[role.value for role in UserRole], default=os.environ.get("ROLE")
    )
    args = parser.parse_args()
    if not args.email or not args.email.strip() or args.role not in {r.value for r in UserRole}:
        parser.error("Provide EMAIL and ROLE=user|manager|admin, or --email and --role.")
    try:
        user_id, previous, current = asyncio.run(_run(args.email, UserRole(args.role)))
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except SQLAlchemyError:
        parser.exit(
            1, "Database operation failed; check the target environment and schema migrations.\n"
        )
    print(f"User {user_id}: {previous} -> {current}")


if __name__ == "__main__":
    main()
