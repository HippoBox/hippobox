"""Pinned location IDs adopted from country-region-data; see notes/account-profile.md."""

import json
from pathlib import Path

LOCATION_CODES = frozenset(
    json.loads(Path(__file__).with_name("profile_location_codes.json").read_text())
)
