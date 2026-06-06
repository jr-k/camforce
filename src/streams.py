from __future__ import annotations

from collections.abc import Iterable, Iterator

from .creds import Preset
from .models import StreamDef


CUSTOM_BRAND = "custom"


class StreamCatalog:
    def __init__(self, streams: Iterable[StreamDef]) -> None:
        self._streams: list[StreamDef] = list(streams)

    @classmethod
    def from_presets(cls, presets: dict[str, Preset]) -> "StreamCatalog":
        streams: list[StreamDef] = []
        for name, preset in presets.items():
            for p in preset.paths:
                streams.append(StreamDef(label=p.label, path=p.path, brand=name))
        return cls(streams)

    def filtered(self, vendors: dict[str, bool] | None) -> "StreamCatalog":
        """Keep everything if vendors=None, otherwise only brands set to True.
        Custom paths (added via add_custom) always pass through."""
        if vendors is None:
            return StreamCatalog(self._streams)
        keep = lambda s: s.brand == CUSTOM_BRAND or vendors.get(s.brand, False)
        return StreamCatalog(s for s in self._streams if keep(s))

    def add_custom(self, path: str) -> None:
        self._streams.append(StreamDef(f"Custom {path}", path, CUSTOM_BRAND))

    def __iter__(self) -> Iterator[StreamDef]:
        return iter(self._streams)

    def __len__(self) -> int:
        return len(self._streams)


def known_vendors(presets: dict[str, Preset]) -> tuple[str, ...]:
    return tuple(sorted(presets.keys()))
