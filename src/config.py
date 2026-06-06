from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Instance:
    host: str
    username: str | None = None
    password: str | None = None
    name: str = ""
    port: int = 554
    timeout: float = 10.0
    workers: int = 16
    well_known: bool = False
    vendors_presets: dict[str, bool] | None = None
    paths: list[str] = field(default_factory=list)
    credentials: list[tuple[str, str]] = field(default_factory=list)

    def display_name(self) -> str:
        return self.name or f"{self.host}:{self.port}"

    @classmethod
    def from_dict(cls, data: dict) -> "Instance":
        allowed = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"Unknown fields in config: {sorted(unknown)}")
        if "host" not in data:
            raise ValueError("Missing required field: 'host'")
        has_user = "username" in data and data["username"] is not None
        has_pwd = "password" in data and data["password"] is not None
        if has_user ^ has_pwd:
            raise ValueError(
                "'username' and 'password' must be provided together "
                "(or both omitted)."
            )
        parsed = dict(data)
        if "credentials" in parsed:
            parsed["credentials"] = _parse_credentials(parsed["credentials"])
        return cls(**parsed)


def _parse_credentials(raw: object) -> list[tuple[str, str]]:
    """Parse ad-hoc credentials defined inline in config.yaml.

    Accepted forms:
      credentials:                # mapping
        admin: admin
        root: ""
      credentials:                # list of "user:password" strings
        - admin:admin
        - root:
    """
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [(str(u), "" if p is None else str(p)) for u, p in raw.items()]
    if isinstance(raw, list):
        results: list[tuple[str, str]] = []
        for item in raw:
            if not isinstance(item, str) or ":" not in item:
                raise ValueError(
                    f"Invalid credentials entry: {item!r} "
                    f"(expected 'user:password')."
                )
            user, password = item.split(":", 1)
            results.append((user, password))
        return results
    raise ValueError(
        f"'credentials' must be a mapping or a list, got {type(raw).__name__}."
    )


class Config:
    def __init__(self, instances: list[Instance]) -> None:
        if not instances:
            raise ValueError("Config must contain at least one instance.")
        self.instances = instances

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        raw_instances = data.get("instances")
        if not isinstance(raw_instances, list):
            raise ValueError("The 'instances' key must be a list.")

        instances = [Instance.from_dict(item) for item in raw_instances]
        return cls(instances)

    def __iter__(self):
        return iter(self.instances)

    def __len__(self) -> int:
        return len(self.instances)
