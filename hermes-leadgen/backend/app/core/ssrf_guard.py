"""SSRF protection for every outbound fetch the app performs.

Used by the research pipeline (company website fetcher) and any future
provider connector that fetches a user-supplied or discovered URL. Blocks:

- non-http(s) schemes
- localhost / loopback
- RFC1918 private ranges, link-local, and other non-global unicast ranges
- cloud metadata endpoints (169.254.169.254 and friends)
- credentials embedded in the URL (userinfo), which can be used to smuggle
  auth into unexpected hosts

DNS is resolved and *every* resolved address is checked (not just the
literal host string) to prevent DNS-rebinding bypasses.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
}

# Cloud metadata IPs that are not otherwise covered by the private-range checks below.
BLOCKED_LITERAL_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure/OCI metadata
    "100.100.100.200",  # Alibaba Cloud metadata
    "::ffff:169.254.169.254",
}


@dataclass
class SSRFCheckResult:
    allowed: bool
    reason: str = ""
    resolved_ip: str | None = None


def _is_blocked_ip(ip_str: str) -> str | None:
    if ip_str in BLOCKED_LITERAL_IPS:
        return "cloud metadata address"
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return "unparseable IP"
    if ip.is_loopback:
        return "loopback address"
    if ip.is_private:
        return "private address range"
    if ip.is_link_local:
        return "link-local address"
    if ip.is_multicast:
        return "multicast address"
    if ip.is_reserved:
        return "reserved address range"
    if ip.is_unspecified:
        return "unspecified address"
    return None


def check_url(url: str) -> SSRFCheckResult:
    """Validate a URL is safe to fetch: public http(s) host, no embedded creds."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return SSRFCheckResult(False, "malformed URL")

    if parsed.scheme not in ("http", "https"):
        return SSRFCheckResult(False, f"scheme '{parsed.scheme}' not allowed")

    if parsed.username or parsed.password:
        return SSRFCheckResult(False, "URL must not embed credentials")

    hostname = parsed.hostname
    if not hostname:
        return SSRFCheckResult(False, "missing hostname")

    if hostname.lower() in BLOCKED_HOSTNAMES:
        return SSRFCheckResult(False, "blocked hostname")

    # If the host is already a literal IP, check it directly.
    try:
        literal_ip = ipaddress.ip_address(hostname)
        reason = _is_blocked_ip(str(literal_ip))
        if reason:
            return SSRFCheckResult(False, reason, resolved_ip=str(literal_ip))
        return SSRFCheckResult(True, resolved_ip=str(literal_ip))
    except ValueError:
        pass  # not a literal IP, fall through to DNS resolution

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return SSRFCheckResult(False, "DNS resolution failed")

    resolved_ips = {info[4][0] for info in addr_infos}
    if not resolved_ips:
        return SSRFCheckResult(False, "DNS resolution returned no addresses")

    for ip_str in resolved_ips:
        reason = _is_blocked_ip(ip_str)
        if reason:
            return SSRFCheckResult(False, f"{reason} ({ip_str})", resolved_ip=ip_str)

    return SSRFCheckResult(True, resolved_ip=next(iter(resolved_ips)))


def assert_safe_url(url: str) -> None:
    result = check_url(url)
    if not result.allowed:
        raise ValueError(f"Refusing to fetch '{url}': {result.reason}")
