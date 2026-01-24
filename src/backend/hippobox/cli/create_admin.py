import argparse
import asyncio
import sys

from hippobox.core.bootstrap_admin import AdminBootstrapError, bootstrap_admin_user
from hippobox.core.database import dispose_db, init_db
from hippobox.core.logging_config import setup_logger
from hippobox.core.settings import SETTINGS


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first admin user for HippoBox.")
    parser.add_argument("--email", default=SETTINGS.ADMIN_EMAIL, help="Admin email (default: ADMIN_EMAIL)")
    parser.add_argument("--password", default=SETTINGS.ADMIN_PASSWORD, help="Admin password (default: ADMIN_PASSWORD)")
    parser.add_argument("--name", default=SETTINGS.ADMIN_NAME, help="Admin name (default: ADMIN_NAME)")
    parser.add_argument(
        "--verify-email",
        dest="verify_email",
        action="store_true",
        default=SETTINGS.ADMIN_VERIFY_EMAIL,
        help="Mark admin email as verified",
    )
    parser.add_argument(
        "--no-verify-email",
        dest="verify_email",
        action="store_false",
        help="Do not mark admin email as verified",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> bool:
    await init_db()
    try:
        return await bootstrap_admin_user(
            args.email,
            args.password,
            args.name,
            verify_email=args.verify_email,
        )
    finally:
        await dispose_db()


def main() -> int:
    setup_logger()
    args = _parse_args()
    try:
        created = asyncio.run(_run(args))
    except AdminBootstrapError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    if created:
        print("Admin user created.")
    else:
        print("Admin user already exists. No changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
