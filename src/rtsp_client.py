from __future__ import annotations

import base64
import socket
import time
from urllib.parse import quote

from .auth import DigestChallenge
from .models import ProbeResult
from .protocol import classify, parse_code


METHOD = "DESCRIBE"
RECV_CHUNK = 4096
MAX_HEADER_BYTES = 65536
EMPTY_RESPONSE_RETRIES = 1


class RtspClient:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: float,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout

    def build_url(self, path: str) -> str:
        user = quote(self.username, safe="")
        pwd = quote(self.password, safe="")
        return f"rtsp://{user}:{pwd}@{self.host}:{self.port}{self._normalize_path(path)}"

    def probe(self, label: str, path: str) -> ProbeResult:
        start = time.time()
        url = self.build_url(path)
        try:
            response = self._describe_with_retry(path)
            elapsed = time.time() - start
            return classify(label, path, url, response, elapsed)
        except socket.timeout:
            return ProbeResult(
                label, path, url, "TIMEOUT",
                detail=f">{self.timeout:.0f}s",
                elapsed=time.time() - start,
            )
        except ConnectionRefusedError:
            return ProbeResult(
                label, path, url, "REFUSED",
                detail="Port closed or service unavailable",
                elapsed=time.time() - start,
            )
        except OSError as e:
            return ProbeResult(label, path, url, "ERROR", detail=str(e), elapsed=time.time() - start)

    def _describe_with_retry(self, path: str) -> bytes:
        response = self._describe(path)
        attempts = 0
        while not response and attempts < EMPTY_RESPONSE_RETRIES:
            attempts += 1
            response = self._describe(path)
        return response

    def _describe(self, path: str) -> bytes:
        # Combos (full URI vs path-only) x (algorithm included vs omitted), to
        # cover exotic firmwares (EvoStream/UVC in particular).
        variants = [(uri, omit) for uri in (self._uri_for(path), self._normalize_path(path)) for omit in (False, True)]
        last = b""
        for digest_uri, omit_algo in variants:
            try:
                last = self._round(path, digest_uri, omit_algo)
            except (BrokenPipeError, ConnectionResetError):
                continue
            if parse_code(last)[0] != "401":
                return last
        return last

    def _round(self, path: str, digest_uri: str, omit_algorithm: bool) -> bytes:
        # RFC-compliant flow: 1) DESCRIBE without auth, 2) read the challenge,
        # 3) DESCRIBE with the auth that matches what the server asks for.
        # Sending Basic upfront makes some cameras close the connection
        # (Ubiquiti in particular).
        with self._connect() as sock:
            first = self._exchange(sock, path, None, cseq=1)
            code, _ = parse_code(first)
            if code != "401":
                return first
            auth_header = self._auth_header_for(first, digest_uri, omit_algorithm)
            if auth_header is None:
                return first
            return self._exchange(sock, path, auth_header, cseq=2)

    def _auth_header_for(self, response: bytes, digest_uri: str, omit_algorithm: bool) -> str | None:
        challenge = DigestChallenge.from_response(response)
        if challenge is not None:
            return challenge.build_header(
                METHOD, digest_uri, self.username, self.password,
                omit_algorithm=omit_algorithm,
            )
        token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return f"Basic {token}"

    def _connect(self) -> socket.socket:
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        return sock

    def _exchange(self, sock: socket.socket, path: str, auth_header: str | None, cseq: int) -> bytes:
        sock.sendall(self._build_request(path, auth_header, cseq))
        return self._recv_headers(sock)

    @staticmethod
    def _recv_headers(sock: socket.socket) -> bytes:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(RECV_CHUNK)
            if not chunk:
                break
            data += chunk
            if len(data) >= MAX_HEADER_BYTES:
                break
        return data

    def _build_request(self, path: str, auth_header: str | None, cseq: int) -> bytes:
        uri = self._uri_for(path)
        lines = [
            f"{METHOD} {uri} RTSP/1.0",
            f"CSeq: {cseq}",
            "User-Agent: camforce/0.1",
            "Accept: application/sdp",
        ]
        if auth_header:
            lines.append(f"Authorization: {auth_header}")
        return ("\r\n".join(lines) + "\r\n\r\n").encode()

    def _uri_for(self, path: str) -> str:
        return f"rtsp://{self.host}:{self.port}{self._normalize_path(path)}"

    @staticmethod
    def _normalize_path(path: str) -> str:
        return path if path.startswith("/") else "/" + path
