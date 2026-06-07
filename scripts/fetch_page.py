#!/usr/bin/env python3
"""
Fetch a landing page for ad campaign quality analysis.

Usage:
    python fetch_page.py https://example.com/landing
    python fetch_page.py https://example.com/landing --output page.html
"""

import argparse
import sys
from urllib.parse import urljoin

from url_utils import sanitize_error, sanitize_url, validate_url

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install -r requirements.txt")
    sys.exit(1)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ClaudeAds/1.7; +https://github.com/AI-Marketing-Hub/claude-ads)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def fetch_page(
    url: str,
    timeout: int = 30,
    follow_redirects: bool = True,
    max_redirects: int = 5,
) -> dict:
    """
    Fetch a landing page and return response details relevant to ad quality checks.

    Returns:
        Dictionary with url, status_code, content, headers, redirect_chain, error
    """
    result = {
        "url": url,
        "status_code": None,
        "content": None,
        "headers": {},
        "redirect_chain": [],
        "error": None,
    }

    # Block SSRF bypass via userinfo with backslash (urlparse vs requests differential)
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        result["error"] = "URL with userinfo is not allowed"
        return result
    if '\\' in parsed.hostname or '\\' in url:
        result["error"] = "URL with backslash is not allowed"
        return result
    try:
        url = validate_url(url)
    except ValueError as e:
        result["error"] = sanitize_error(e)
        return result

    try:
        session = requests.Session()
        current_url = url
        redirect_chain = []

        # Manual redirect loop with per-hop SSRF revalidation. The previous
        # `allow_redirects=True` path delegated to urllib3, which fetched
        # `Location` targets without re-checking them against the private-IP
        # blocklist. A public origin returning a 302 to e.g. 169.254.169.254
        # would have reached cloud metadata.
        for _ in range(max_redirects + 1):
            response = session.get(
                current_url,
                headers=DEFAULT_HEADERS,
                timeout=timeout,
                allow_redirects=False,
            )

            if not follow_redirects or response.status_code not in (301, 302, 303, 307, 308):
                break

            location = response.headers.get("Location")
            if not location:
                break

            next_url = urljoin(current_url, location)
            try:
                next_url = validate_url(next_url)
            except ValueError as e:
                result["error"] = f"Blocked redirect: {sanitize_error(e)}"
                return result

            redirect_chain.append(current_url)
            current_url = next_url
        else:
            result["error"] = f"Too many redirects (max {max_redirects})"
            return result

        result["url"] = current_url
        result["status_code"] = response.status_code
        result["content"] = response.text
        result["headers"] = dict(response.headers)
        result["redirect_chain"] = redirect_chain

    except requests.exceptions.Timeout:
        result["error"] = f"Request timed out after {timeout} seconds"
    except requests.exceptions.SSLError as e:
        result["error"] = f"SSL error: {sanitize_error(e)}"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection error: {sanitize_error(e)}"
    except requests.exceptions.RequestException as e:
        result["error"] = f"Request failed: {sanitize_error(e)}"

    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch a landing page for ad quality analysis")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--no-redirects", action="store_true", help="Don't follow redirects")

    args = parser.parse_args()

    result = fetch_page(
        args.url,
        timeout=args.timeout,
        follow_redirects=not args.no_redirects,
    )

    if result["error"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result["content"])
        print(f"Saved to {args.output}")
    else:
        print(result["content"])

    print(f"\nURL: {sanitize_url(result['url'])}", file=sys.stderr)
    print(f"Status: {result['status_code']}", file=sys.stderr)
    if result["redirect_chain"]:
        sanitized_chain = [sanitize_url(u) for u in result["redirect_chain"]]
        print(f"Redirects: {' -> '.join(sanitized_chain)}", file=sys.stderr)


if __name__ == "__main__":
    main()
