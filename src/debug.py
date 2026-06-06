from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from rich.console import Console

from .auth import DigestChallenge
from .protocol import parse_code

if TYPE_CHECKING:
    from .rtsp_client import RtspClient


METHOD = "DESCRIBE"


def print_debug_probe(client: RtspClient, path: str, console: Console) -> None:
    """Run a SINGLE probe on path and print everything (with a FRESH nonce per attempt)."""
    request_initial = client._build_request(path, None, 1)
    _print_block(console, "1. Request (no auth)", request_initial, "cyan")

    try:
        with client._connect() as sock:
            sock.sendall(request_initial)
            response_initial = client._recv_headers(sock)
    except OSError as e:
        console.print(f"[red]Initial network error: {e}[/red]")
        return
    _print_block(console, "1. Response", response_initial, "yellow")

    code, _ = parse_code(response_initial)
    if code != "401":
        console.print(f"[bold]No challenge required (code {code or '∅'})[/bold]")
        return

    preview = DigestChallenge.from_response(response_initial)
    if preview is None:
        console.rule("[bold]2. No Digest -> trying Basic[/bold]")
        token = base64.b64encode(f"{client.username}:{client.password}".encode()).decode()
        _attempt(client, path, lambda _ch: f"Basic {token}", "Basic", console)
        return

    console.rule("[bold]2. Challenge format (a FRESH nonce will be used for each attempt)[/bold]")
    console.print({
        "realm": preview.realm, "qop": preview.qop,
        "algorithm": preview.algorithm, "opaque": preview.opaque,
    })

    uri_full = client._uri_for(path)
    uri_path = client._normalize_path(path)
    variants = [
        ("Full URI + algorithm", uri_full, False),
        ("Full URI without algorithm", uri_full, True),
        ("Path-only URI + algorithm", uri_path, False),
        ("Path-only URI without algorithm", uri_path, True),
    ]
    for label, uri_variant, omit_algo in variants:
        builder = lambda ch, u=uri_variant, o=omit_algo: ch.build_header(
            METHOD, u, client.username, client.password, omit_algorithm=o,
        )
        if _attempt(client, path, builder, label, console):
            return


def _attempt(client: RtspClient, path: str, header_builder, label: str, console: Console) -> bool:
    """Open ONE socket, send no-auth -> get fresh nonce, send auth, print everything."""
    try:
        with client._connect() as sock:
            sock.sendall(client._build_request(path, None, 1))
            no_auth_resp = client._recv_headers(sock)

            challenge = DigestChallenge.from_response(no_auth_resp)
            if challenge is None and "basic" not in label.lower():
                console.print(f"[red]✗ No Digest in response for variant {label}[/red]")
                return False

            auth_header = header_builder(challenge)
            auth_req = client._build_request(path, auth_header, 2)
            _print_block(console, f"3. Request ({label})", auth_req, "cyan")

            sock.sendall(auth_req)
            response = client._recv_headers(sock)
    except OSError as e:
        console.print(f"[red]Network error ({label}): {e}[/red]")
        return False

    _print_block(console, f"3. Response ({label})", response, "green")
    if parse_code(response)[0] != "401":
        console.print(f"[bold green]✓ Variant accepted: {label}[/bold green]")
        return True
    console.print(f"[red]✗ 401 on this variant[/red]")
    return False


def _print_block(console: Console, title: str, payload: bytes, style: str) -> None:
    console.rule(f"[bold]{title}[/bold]")
    text = payload.decode(errors="replace").rstrip()
    console.print(text or "[dim](empty)[/dim]", style=style, highlight=False)
