from __future__ import annotations

from collections.abc import Sequence

from rich import box
from rich.table import Table

from .models import ProbeResult


class TableRenderer:
    STATUS_STYLES: dict[str, str] = {
        "PENDING": "dim",
        "RUNNING": "cyan",
        "OK": "bold green",
        "UNAUTHORIZED": "yellow",
        "RTSP_REPLY": "blue",
        "NOT_FOUND": "red",
        "FORBIDDEN": "red",
        "NO_RESPONSE": "magenta",
        "TIMEOUT": "red",
        "REFUSED": "red",
        "ERROR": "red",
        "UNKNOWN_REPLY": "magenta",
    }

    def __init__(self, title: str = "RTSP Probe") -> None:
        self.title = title

    @classmethod
    def status_style(cls, status: str) -> str:
        return cls.STATUS_STYLES.get(status, "white")

    def render(
        self,
        results: Sequence[ProbeResult],
        remaining_seconds: float | None = None,
    ) -> Table:
        title = self.title
        if remaining_seconds is not None:
            title = f"{self.title}  [dim](timeout in {remaining_seconds:.1f}s)[/dim]"

        table = Table(
            title=title,
            box=box.ROUNDED,
            expand=True,
            show_lines=False,
        )

        table.add_column("#", justify="right", style="dim", width=4)
        table.add_column("Status", width=14)
        table.add_column("Label", min_width=20)
        table.add_column("URI", overflow="fold", min_width=40)
        table.add_column("Code", width=6)
        table.add_column("Time", width=8)
        table.add_column("Detail", overflow="fold")

        for i, r in enumerate(results, 1):
            style = self.status_style(r.status)
            table.add_row(
                str(i),
                f"[{style}]{r.status}[/{style}]",
                r.label,
                r.url,
                r.code or "-",
                f"{r.elapsed:.2f}s" if r.elapsed else "-",
                r.detail or "-",
            )

        return table
