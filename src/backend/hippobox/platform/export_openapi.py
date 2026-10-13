"""Export the baseline without starting the application or connecting to services."""

import argparse
import json
from pathlib import Path

from hippobox.platform.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    schema = create_app().openapi()
    # Deployment branding is not part of the shared API contract.
    schema["info"]["title"] = "B4 API"
    rendered = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            parser.exit(1, "OpenAPI baseline is stale; run make contract-export.\n")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
