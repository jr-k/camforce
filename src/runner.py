from __future__ import annotations

import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from rich.console import Console
from rich.live import Live

from .config import Instance
from .models import ProbeResult, StreamDef
from .renderer import TableRenderer
from .rtsp_client import RtspClient


@dataclass(frozen=True)
class ProbeTask:
    label: str
    path: str
    username: str
    password: str


class _LiveBoard:
    """Rich renderable that recomputes the countdown + table on each refresh."""

    def __init__(self, renderer: TableRenderer, results: list[ProbeResult], deadline: float) -> None:
        self.renderer = renderer
        self.results = results
        self.deadline = deadline

    def __rich__(self):
        remaining = max(0.0, self.deadline - time.time())
        return self.renderer.render(self.results, remaining_seconds=remaining)


class ProbeRunner:
    def __init__(
        self,
        instance: Instance,
        streams: Iterable[StreamDef],
        well_known: bool = False,
        wellknown_creds: dict[str, list[tuple[str, str]]] | None = None,
        renderer: TableRenderer | None = None,
    ) -> None:
        self.instance = instance
        self.streams: list[StreamDef] = list(streams)
        self.well_known = well_known
        self.wellknown_creds = wellknown_creds or {}
        self.renderer = renderer or TableRenderer()

    def run(self, console: Console) -> list[ProbeResult]:
        tasks = self._build_tasks()
        results = [
            ProbeResult(
                label=t.label,
                path=t.path,
                url=self._client_for(t).build_url(t.path),
                status="PENDING",
            )
            for t in tasks
        ]
        deadline = time.time() + self.instance.timeout
        board = _LiveBoard(self.renderer, results, deadline)

        with ThreadPoolExecutor(max_workers=self.instance.workers) as executor:
            future_to_idx = {}
            for idx, task in enumerate(tasks):
                results[idx].status = "RUNNING"
                future = executor.submit(self._probe_task, task)
                future_to_idx[future] = idx

            with Live(board, console=console, refresh_per_second=10) as live:
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    results[idx] = future.result()
                    board.results = results
                    live.refresh()

        return results

    def _build_tasks(self) -> list[ProbeTask]:
        presets = self.instance.vendors_presets or {}
        # Omitting vendors_presets entirely means "no restriction": probe
        # the full catalog AND test every vendor's credential dictionary,
        # same effect as well_known: true.
        test_all_brands = self.instance.vendors_presets is None
        custom_creds = self.instance.credentials or []
        baseline = None
        if self.instance.username is not None and self.instance.password is not None:
            baseline = (self.instance.username, self.instance.password)
        tasks: list[ProbeTask] = []
        seen_per_path: dict[str, set[tuple[str, str]]] = {}
        for stream in self.streams:
            seen = seen_per_path.setdefault(stream.path, set())
            if baseline is not None and baseline not in seen:
                tasks.append(ProbeTask(stream.label, stream.path, *baseline))
                seen.add(baseline)
            for user, pwd in custom_creds:
                cred = (user, pwd)
                if cred in seen:
                    continue
                label = f"{stream.label} [{user}:{pwd or '∅'}]"
                tasks.append(ProbeTask(label, stream.path, user, pwd))
                seen.add(cred)
            if not stream.brand:
                continue
            preset_active = bool(presets.get(stream.brand))
            if not (self.well_known or preset_active or test_all_brands):
                continue
            for user, pwd in self.wellknown_creds.get(stream.brand, ()):
                cred = (user, pwd)
                if cred in seen:
                    continue
                label = f"{stream.label} [{user}:{pwd or '∅'}]"
                tasks.append(ProbeTask(label, stream.path, user, pwd))
                seen.add(cred)
        return tasks

    def _probe_task(self, task: ProbeTask) -> ProbeResult:
        return self._client_for(task).probe(task.label, task.path)

    def _client_for(self, task: ProbeTask) -> RtspClient:
        return RtspClient(
            host=self.instance.host,
            port=self.instance.port,
            username=task.username,
            password=task.password,
            timeout=self.instance.timeout,
        )
