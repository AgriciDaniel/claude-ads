"""Shared URL validation utilities with SSRF protection.

Used by fetch_page.py, analyze_landing.py, and capture_screenshot.py to
validate user-supplied URLs before making HTTP requests or launching browsers.
"""

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_NETS = [
    # IPv4 private/reserved
    ipaddress.ip_network("0.0.0.0/8"),       # "this network" — aliases localhost on Linux
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT / shared address space (cloud VPCs)
    # IPv6 private/reserved
    ipaddress.ip_network("::/128"),         # unspecified address (some kernels coerce to localhost)
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
]


def validate_url(url: str) -> str:
    """Validate URL scheme and block private/internal IPs (SSRF protection).

    Args:
        url: The URL to validate. If no scheme, https:// is prepended.

    Returns:
        The validated URL string (with scheme).

    Raises:
        ValueError: If URL has invalid scheme, no hostname, resolves to
                    a blocked IP, or DNS resolution fails.
    """
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _, _, _, _, addr in resolved:
            ip = ipaddress.ip_address(addr[0])
            for net in _BLOCKED_NETS:
                if ip in net:
                    raise ValueError(f"URL resolves to blocked private/internal IP: {ip}")
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for {hostname}: {exc}") from exc
    return url
