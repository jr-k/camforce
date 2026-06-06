from __future__ import annotations

from .models import ProbeResult


_STATUS_BY_CODE = {
    "200": "OK",
    "401": "UNAUTHORIZED",
    "403": "FORBIDDEN",
    "404": "NOT_FOUND",
}


def parse_code(response: bytes) -> tuple[str, str]:
    text = response.decode(errors="replace")
    lines = text.splitlines()
    first_line = lines[0] if lines else ""
    parts = first_line.split(" ", 2)
    if len(parts) >= 2 and parts[0].startswith("RTSP/"):
        code = parts[1]
        reason = parts[2] if len(parts) >= 3 else ""
        return code, reason
    return "", first_line[:80]


def classify(
    label: str,
    path: str,
    url: str,
    response: bytes,
    elapsed: float,
) -> ProbeResult:
    if not response:
        return ProbeResult(
            label, path, url, "NO_RESPONSE",
            detail="Server closed the connection without replying",
            elapsed=elapsed,
        )
    code, reason = parse_code(response)
    if code in _STATUS_BY_CODE:
        return ProbeResult(label, path, url, _STATUS_BY_CODE[code], code=code, detail=reason, elapsed=elapsed)
    if code:
        return ProbeResult(label, path, url, "RTSP_REPLY", code=code, detail=reason, elapsed=elapsed)
    return ProbeResult(label, path, url, "UNKNOWN_REPLY", detail=reason, elapsed=elapsed)
