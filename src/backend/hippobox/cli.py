import argparse

import uvicorn

from hippobox import __version__
from hippobox.server import app


def main():
    parser = argparse.ArgumentParser(
        prog="hippobox",
        description="HippoBox MCP + Knowledge Store Server",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"hippobox {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Run HippoBox server",
    )

    run_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )

    run_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000)",
    )

    args = parser.parse_args()

    if args.command == "run":
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=False,
        )
