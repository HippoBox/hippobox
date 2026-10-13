"""Inspect/retry lifecycle failures using trusted deployment-operator access, not HTTP roles."""

import argparse
import asyncio
import getpass
import json
import re

from sqlalchemy.exc import SQLAlchemyError

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.db.session import dispose_db
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.models.notification import Notifications

logger = get_logger("hippobox.platform.operator.notifications")


async def retry_notification(key: str) -> bool:
    if not re.fullmatch(r"[0-9a-f]{64}", key):
        raise ValueError("Use a 64-character notification ID from the failure list.")
    if not SETTINGS.EMAIL_ENABLED:
        raise ValueError("Email must be enabled before retrying a notification.")
    changed = await Notifications.retry(key)
    logger.warning(
        "Lifecycle mail retry requested (operator=%s, id=%s, queued=%s).",
        getpass.getuser(),
        key,
        changed,
    )
    # Beat will publish the work. CLI never sends SMTP or prints recipient payloads.
    return changed


async def _run(args: argparse.Namespace) -> list[dict] | bool:
    try:
        if args.command == "list":
            return await Notifications.failures(args.limit)
        return await retry_notification(args.id)
    finally:
        await dispose_db()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="List failed/expired metadata without recipients")
    listing.add_argument("--limit", type=int, default=50)
    retry = commands.add_parser("retry", help="Requeue one retained failed notification")
    retry.add_argument("id")
    args = parser.parse_args()
    try:
        result = asyncio.run(_run(args))
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed; verify environment and migrations.\n")
    if isinstance(result, list):
        print(json.dumps(result, default=str, indent=2))
    elif result:
        print("Notification queued for the next worker scan; original expiry retained.")
    else:
        parser.exit(1, "No retained failed notification matched; nothing changed.\n")


if __name__ == "__main__":
    main()
