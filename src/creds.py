from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


def _vendors_dir() -> Path:
    """Locate the vendors directory.

    Search order:
      1. <cwd>/vendors             (running from project root, or Docker mount)
      2. <package-root>/vendors    (editable install / source checkout)
    """
    candidates = [
        Path.cwd() / "vendors",
        Path(__file__).resolve().parent.parent / "vendors",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    raise FileNotFoundError(
        "No 'vendors' folder found. Run camforce from the project root, or "
        "install it editable (pip install -e .), so that vendors/<brand>/"
        "{credentials,paths}.txt is reachable."
    )


@dataclass(frozen=True)
class PresetPath:
    label: str
    path: str


@dataclass
class Preset:
    name: str
    paths: list[PresetPath] = field(default_factory=list)
    credentials: list[tuple[str, str]] = field(default_factory=list)


def load_presets() -> dict[str, Preset]:
    """Scan vendors/<brand>/{credentials,paths}.txt.

    Each subfolder of vendors/ is a preset, named after the folder.
    Both files are optional but a preset must contain at least one.
    """
    presets: dict[str, Preset] = {}
    root = _vendors_dir()
    for vendor_dir in sorted(root.iterdir()):
        if not vendor_dir.is_dir():
            continue
        name = vendor_dir.name
        preset = Preset(name=name)
        paths_file = vendor_dir / "paths.txt"
        creds_file = vendor_dir / "credentials.txt"
        if paths_file.is_file():
            preset.paths = _parse_paths(paths_file, name)
        if creds_file.is_file():
            preset.credentials = _parse_credentials(creds_file)
        if preset.paths or preset.credentials:
            presets[name] = preset

    if not presets:
        raise FileNotFoundError(
            f"No preset found under {root}. Expected at least one "
            f"<brand>/ folder containing credentials.txt and/or paths.txt."
        )
    return presets


def _iter_records(path: Path) -> Iterable[str]:
    """Yield non-empty, non-comment lines (stripped of trailing newline)."""
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            yield line


def _parse_paths(file: Path, preset_name: str) -> list[PresetPath]:
    """Each line: <path>[<TAB><label>]. Label is optional."""
    results: list[PresetPath] = []
    for line in _iter_records(file):
        if "\t" in line:
            path, label = line.split("\t", 1)
            label = label.strip()
        else:
            path, label = line, ""
        path = path.strip()
        if not path:
            raise ValueError(f"{file}: empty path on a non-comment line.")
        results.append(PresetPath(label=label or f"{preset_name} {path}", path=path))
    return results


def _parse_credentials(file: Path) -> list[tuple[str, str]]:
    """Each line: user:password (split on the FIRST ':', Hydra convention)."""
    results: list[tuple[str, str]] = []
    for line in _iter_records(file):
        if ":" not in line:
            raise ValueError(
                f"{file}: line missing ':' separator -> {line!r} "
                f"(expected user:password, password may be empty)."
            )
        user, password = line.split(":", 1)
        results.append((user, password))
    return results
