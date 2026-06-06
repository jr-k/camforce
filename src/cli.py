from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from rich.console import Console

from .config import Config, Instance
from .creds import load_presets
from .debug import print_debug_probe
from .rtsp_client import RtspClient
from .runner import ProbeRunner
from .streams import StreamCatalog


class Cli:
    def __init__(self, argv: Sequence[str] | None = None) -> None:
        parser = self._build_parser()
        self.args = parser.parse_args(argv)
        self._validate(parser)

    def run(self) -> None:
        console = Console()
        instances = self._collect_instances()
        presets = load_presets()
        wellknown_creds = {name: p.credentials for name, p in presets.items()}
        base_catalog = StreamCatalog.from_presets(presets)

        if self.args.debug:
            instance = instances[0]
            client = self._build_client(instance)
            console.rule(f"[bold]DEBUG {instance.display_name()} {self.args.debug}[/bold]")
            print_debug_probe(client, self.args.debug, console)
            return

        for idx, instance in enumerate(instances, 1):
            if len(instances) > 1:
                console.rule(f"[bold]{idx}/{len(instances)} - {instance.display_name()}[/bold]")
            self._run_instance(console, instance, base_catalog, wellknown_creds)

    def _run_instance(
        self,
        console: Console,
        instance: Instance,
        base_catalog: StreamCatalog,
        wellknown_creds: dict[str, list[tuple[str, str]]],
    ) -> None:
        catalog = base_catalog.filtered(instance.vendors_presets)
        for custom_path in instance.paths:
            catalog.add_custom(custom_path)

        runner = ProbeRunner(
            instance=instance,
            streams=catalog,
            well_known=instance.well_known,
            wellknown_creds=wellknown_creds,
        )
        runner.run(console)

    @staticmethod
    def _build_client(instance: Instance) -> RtspClient:
        username, password = Cli._debug_credentials(instance)
        return RtspClient(
            host=instance.host,
            port=instance.port,
            username=username,
            password=password,
            timeout=instance.timeout,
        )

    @staticmethod
    def _debug_credentials(instance: Instance) -> tuple[str, str]:
        if instance.username is not None and instance.password is not None:
            return instance.username, instance.password
        if instance.credentials:
            return instance.credentials[0]
        return "", ""

    def _collect_instances(self) -> list[Instance]:
        if self.args.config:
            return list(Config.load(self.args.config))

        return [Instance(
            host=self.args.host,
            username=self.args.username,
            password=self.args.password,
            port=self.args.port,
            timeout=self.args.timeout,
            workers=self.args.workers,
            well_known=self.args.well_known,
            vendors_presets=({v: True for v in self.args.vendor} or None),
            paths=list(self.args.path),
        )]

    def _validate(self, parser: argparse.ArgumentParser) -> None:
        if self.args.config:
            return
        missing = [
            flag for flag, value in (
                ("--host/-H", self.args.host),
                ("--username/-u", self.args.username),
                ("--password/-p", self.args.password),
            ) if not value
        ]
        if missing:
            parser.error(
                "Without -c/--config, the following options are required: "
                + ", ".join(missing)
            )

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="camforce",
            description="Probe RTSP streams across multiple paths, vendors and credentials.",
        )
        parser.add_argument(
            "-c", "--config",
            help="YAML configuration file describing one or more instances.",
        )
        parser.add_argument(
            "--host", "-H",
            help="Hostname or IP of the camera or NVR",
        )
        parser.add_argument("--port", "-P", type=int, default=554, help="RTSP port, default: 554")
        parser.add_argument("--username", "-u", help="RTSP username")
        parser.add_argument("--password", "-p", help="RTSP password")
        parser.add_argument(
            "--timeout", "-t",
            type=float, default=10.0,
            help="Per-probe timeout in seconds, default: 10",
        )
        parser.add_argument(
            "--workers", "-w",
            type=int, default=16,
            help="Number of parallel probes, default: 16",
        )
        parser.add_argument(
            "--vendor", "-V",
            action="append", default=[], metavar="NAME",
            help=(
                "Enable a vendor preset (repeatable). For each preset enabled, "
                "camforce also probes that vendor's well-known dictionary "
                "credentials in addition to the supplied user/password. "
                "Without any -V, no dictionary is tested (only the supplied "
                "user/password against the full path catalog). "
                "Available presets: see the dictionaries/ directory."
            ),
        )
        parser.add_argument(
            "--well-known", "-W",
            action="store_true",
            help=(
                "Probe well-known factory credentials for EVERY brand (global "
                "override). Implied per-brand by --vendor."
            ),
        )
        parser.add_argument(
            "--path",
            action="append", default=[],
            help="Add a custom path. Example: --path /my/stream",
        )
        parser.add_argument(
            "--debug",
            metavar="PATH",
            help="Debug mode: probe a SINGLE path and print raw requests/responses.",
        )
        return parser


def main(argv: Sequence[str] | None = None) -> None:
    try:
        Cli(argv).run()
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(2)
