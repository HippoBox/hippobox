"""Reject arbitrary refs and mismatched versions before publishing artifacts."""
import os
import re
import tomllib
from pathlib import Path

version = tomllib.loads(Path("src/backend/pyproject.toml").read_text())["project"]["version"]
tag = os.environ["TAG"]
if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-rc\.\d+)?", tag) or tag != f"v{version}":
    raise SystemExit("Release tag must match the package version")
with open(os.environ["GITHUB_OUTPUT"], "a") as output:
    output.write(f"version={version}\nprerelease={str('-' in version).lower()}\n")
