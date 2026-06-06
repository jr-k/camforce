from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StreamDef:
    label: str
    path: str
    brand: str = "generic"


@dataclass
class ProbeResult:
    label: str
    path: str
    url: str
    status: str
    code: str = ""
    detail: str = ""
    elapsed: float = 0.0
