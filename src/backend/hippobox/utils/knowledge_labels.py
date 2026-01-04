DEFAULT_TOPIC_NAME = "Uncategorized"
DEFAULT_TOPIC_NORMALIZED = "uncategorized"


def clean_label(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_label(value: str) -> str:
    return clean_label(value).lower()


def normalize_tag(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("#"):
        stripped = stripped[1:]
    return normalize_label(stripped)


def unique_labels(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = normalize_tag(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(clean_label(value).lstrip("#"))
    return unique
