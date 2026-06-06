from __future__ import annotations

import hashlib
import re
import secrets


_PARAM_RE = re.compile(r'(\w+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^,\s]+))')


def _md5_hex(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()


class DigestChallenge:
    def __init__(self, params: dict[str, str]) -> None:
        self.realm = params.get("realm", "")
        self.nonce = params.get("nonce", "")
        self.opaque = params.get("opaque")
        self.qop = params.get("qop")
        # Keep the server's raw algo, or None if it sent nothing. Some firmwares
        # reject the response if we add an algorithm field they never mentioned.
        self.algorithm = params.get("algorithm")

    @classmethod
    def from_response(cls, response: bytes) -> "DigestChallenge | None":
        text = response.decode(errors="replace")
        for line in text.splitlines():
            if not line.lower().startswith("www-authenticate:"):
                continue
            value = line.split(":", 1)[1].strip()
            if value.lower().startswith("digest "):
                params = {
                    m.group(1).lower(): (m.group(2) if m.group(2) is not None else m.group(3))
                    for m in _PARAM_RE.finditer(value[7:])
                }
                return cls(params)
        return None

    def build_header(
        self,
        method: str,
        uri: str,
        username: str,
        password: str,
        *,
        omit_algorithm: bool = False,
    ) -> str:
        algo = (self.algorithm or "MD5").upper()
        use_qop = bool(self.qop)
        cnonce = secrets.token_hex(8) if (use_qop or algo == "MD5-SESS") else None
        nc = "00000001"

        ha1_base = _md5_hex(f"{username}:{self.realm}:{password}")
        if algo == "MD5-SESS":
            ha1 = _md5_hex(f"{ha1_base}:{self.nonce}:{cnonce}")
        else:
            ha1 = ha1_base

        ha2 = _md5_hex(f"{method}:{uri}")

        if use_qop:
            qop = self.qop.split(",")[0].strip()
            response = _md5_hex(f"{ha1}:{self.nonce}:{nc}:{cnonce}:{qop}:{ha2}")
        else:
            response = _md5_hex(f"{ha1}:{self.nonce}:{ha2}")

        parts = [
            f'username="{username}"',
            f'realm="{self.realm}"',
            f'nonce="{self.nonce}"',
            f'uri="{uri}"',
            f'response="{response}"',
        ]
        if self.algorithm and not omit_algorithm:
            parts.append(f"algorithm={self.algorithm}")
        if use_qop:
            parts.extend([f"qop={self.qop.split(',')[0].strip()}", f"nc={nc}", f'cnonce="{cnonce}"'])
        if self.opaque:
            parts.append(f'opaque="{self.opaque}"')

        return "Digest " + ", ".join(parts)
