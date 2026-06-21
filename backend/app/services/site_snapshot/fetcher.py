"""HTTP fetch primitive shared by discovery and crawl.

Wraps the repo's httpx convention and adds two things the crawler needs:
conditional-GET support and a real SSRF guard. Redirects are followed
*manually* so every hop's host can be re-checked (httpx ``follow_redirects``
would hide an intermediate 302 to a private address). Never raises on HTTP
status — failures are captured into the returned :class:`FetchResult`.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import ssl
import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

import httpx

USER_AGENT = "AIEO-Bot/1.0 (Site Snapshot; +https://github.com/aieo)"
_REDIRECT_STATUS = {301, 302, 303, 307, 308}


class BlockedHostError(Exception):
    """Raised when a host resolves to a private/loopback/reserved address."""


def _allow_private() -> bool:
    return os.environ.get("AIEO_SNAPSHOT_ALLOW_PRIVATE") == "1"


def _is_blocked_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    # `not is_global` is the catch-all (also covers CGNAT 100.64/10, 192.0.0.0/24,
    # etc.); the explicit flags keep the intent readable.
    return (
        not addr.is_global
        or addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def guard_host(url: str) -> Optional[str]:
    """Validate ``url``'s host and return a safe IP to pin the connection to.

    This is the *sole* SSRF defense — it does not rely on regex URL validation.
    Returns the validated IP literal a hostname resolves to (so the caller can
    connect to exactly that address and a second DNS lookup can't rebind to a
    private target), or ``None`` when the host is already an IP literal or when
    private hosts are permitted. Raises :class:`BlockedHostError` if the target
    is (or resolves to) a private/loopback/reserved/non-global address.

    Set ``AIEO_SNAPSHOT_ALLOW_PRIVATE=1`` to permit private hosts (used by the
    offline test fixture which serves from 127.0.0.1).
    """
    if _allow_private():
        return None
    host = urlparse(url).hostname
    if not host:
        raise BlockedHostError(f"URL has no host: {url}")
    # A bare IP literal (incl. IPv6) — check directly; the URL already pins it.
    try:
        ipaddress.ip_address(host)
        if _is_blocked_ip(host):
            raise BlockedHostError(f"Blocked address: {host}")
        return None
    except ValueError:
        pass
    # Hostname — resolve every address (IPv4 + IPv6); reject if ANY is private,
    # and pin the connection to the first safe address (prefer IPv4).
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise BlockedHostError(f"Cannot resolve host {host}: {exc}") from exc
    safe: list[tuple[int, str]] = []
    for info in infos:
        family, ip = info[0], info[4][0]
        if _is_blocked_ip(ip):
            raise BlockedHostError(f"Host {host} resolves to blocked address {ip}")
        safe.append((family, ip))
    if not safe:
        raise BlockedHostError(f"Host {host} did not resolve")
    safe.sort(key=lambda f_ip: 0 if f_ip[0] == socket.AF_INET else 1)
    return safe[0][1]


def _pin(
    url: str, safe_ip: str, headers: Dict[str, str]
) -> tuple[str, Dict[str, str], Dict[str, str]]:
    """Rewrite ``url`` to connect to ``safe_ip`` while preserving Host + TLS SNI."""
    parts = urlparse(url)
    literal = f"[{safe_ip}]" if ":" in safe_ip else safe_ip
    netloc = f"{literal}:{parts.port}" if parts.port else literal
    target = parts._replace(netloc=netloc).geturl()
    pinned_headers = dict(headers)
    pinned_headers["Host"] = parts.netloc  # original host[:port]
    extensions = {"sni_hostname": parts.hostname or ""}
    return target, pinned_headers, extensions


@dataclass
class FetchResult:
    url: str
    final_url: str = ""
    status: int = 0
    headers: Dict[str, str] = field(default_factory=dict)  # lowercased keys
    text: str = ""
    content_type: Optional[str] = None
    error: Optional[str] = None
    truncated: bool = False
    elapsed_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300


class Fetcher:
    """Thin httpx wrapper with SSRF guard, manual redirects and byte caps."""

    def __init__(
        self,
        timeout: float = 30.0,
        max_bytes: int = 10 * 1024 * 1024,
        max_redirects: int = 5,
    ):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            verify=ssl.create_default_context(),
            headers={"User-Agent": USER_AGENT},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def fetch(
        self,
        url: str,
        conditional: Optional[Dict[str, str]] = None,
    ) -> FetchResult:
        """GET ``url`` following redirects manually, guarding each hop.

        Returns a FetchResult. A 304 comes back with ``status == 304`` and empty
        text (the caller reuses its cached body). Network/SSRF errors populate
        ``error`` and never raise.
        """
        start = time.monotonic()
        result = FetchResult(url=url, final_url=url)
        current = url
        headers = dict(conditional or {})
        try:
            for _ in range(self.max_redirects + 1):
                resp = self._open(current, headers)
                try:
                    status = resp.status_code
                    if status in _REDIRECT_STATUS and "location" in resp.headers:
                        current = urljoin(current, resp.headers["location"])
                        continue
                    result.final_url = current
                    result.status = status
                    result.headers = {k.lower(): v for k, v in resp.headers.items()}
                    result.content_type = resp.headers.get("content-type")
                    if status == 304:
                        return self._stamp(result, start)
                    raw, truncated = self._read_capped(resp)
                    result.truncated = truncated
                    encoding = resp.encoding or "utf-8"
                    try:
                        result.text = raw.decode(encoding, errors="replace")
                    except (LookupError, TypeError):
                        result.text = raw.decode("utf-8", errors="replace")
                    return self._stamp(result, start)
                finally:
                    resp.close()
            result.error = f"Too many redirects (>{self.max_redirects})"
        except BlockedHostError as exc:
            result.error = f"blocked: {exc}"
        except httpx.HTTPError as exc:
            result.error = f"{type(exc).__name__}: {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            result.error = f"{type(exc).__name__}: {exc}"
        return self._stamp(result, start)

    def fetch_bytes(
        self, url: str, max_bytes: Optional[int] = None
    ) -> tuple[Optional[bytes], Optional[str], Optional[str]]:
        """Guarded, size-capped raw GET for assets. Returns (bytes, content_type, error).

        Does not follow redirects (assets that redirect are skipped) to keep the
        SSRF guard sound without re-resolving each hop.
        """
        cap = max_bytes or self.max_bytes
        try:
            resp = self._open(url, {})
            try:
                if not (200 <= resp.status_code < 300):
                    return (
                        None,
                        resp.headers.get("content-type"),
                        f"HTTP {resp.status_code}",
                    )
                data, _ = self._read_capped_n(resp, cap)
                return data, resp.headers.get("content-type"), None
            finally:
                resp.close()
        except BlockedHostError as exc:
            return None, None, f"blocked: {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            return None, None, f"{type(exc).__name__}: {exc}"

    def _open(self, url: str, headers: Dict[str, str]) -> httpx.Response:
        """Guard + DNS-pin, then open a streaming GET. Caller must close the response."""
        safe_ip = guard_host(url)
        if safe_ip:
            target, pinned_headers, extensions = _pin(url, safe_ip, headers)
            request = self._client.build_request(
                "GET", target, headers=pinned_headers, extensions=extensions
            )
        else:
            request = self._client.build_request("GET", url, headers=headers)
        return self._client.send(request, stream=True)

    def _read_capped_n(self, resp: httpx.Response, cap: int) -> tuple[bytes, bool]:
        chunks, total, truncated = [], 0, False
        for chunk in resp.iter_bytes():
            if total + len(chunk) >= cap:
                chunks.append(chunk[: cap - total])  # trim so we never exceed cap
                truncated = True
                break
            chunks.append(chunk)
            total += len(chunk)
        return b"".join(chunks), truncated

    def _read_capped(self, resp: httpx.Response) -> tuple[bytes, bool]:
        return self._read_capped_n(resp, self.max_bytes)

    @staticmethod
    def _stamp(result: FetchResult, start: float) -> FetchResult:
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
