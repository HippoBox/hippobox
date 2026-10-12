"""Export the complete API without starting services or reading local secrets."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    os.environ.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "VDB_ENABLED": "true",
            "SWAGGER_ENABLED": "true",
            "APP_MODE": "development",
            "LOGIN_ENABLED": "true",
            "ADMIN_BOOTSTRAP": "false",
        }
    )
    from hippobox.server import create_app

    schema = json.dumps(create_app().openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.path.exists() or args.path.read_text() != schema:
            raise SystemExit("OpenAPI contract drift: run make contract-export and make frontend-api-generate")
    else:
        args.path.parent.mkdir(parents=True, exist_ok=True)
        args.path.write_text(schema)


if __name__ == "__main__":
    main()
