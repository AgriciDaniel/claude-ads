#!/usr/bin/env python3
"""
Analyze landing page quality for ad campaigns using Playwright.

Checks Core Web Vitals, mobile responsiveness, message match elements,
and conversion-readiness signals aligned with ad audit checks G59-G61.

Usage:
    python analyze_landing.py https://example.com/landing
    python analyze_landing.py https://example.com/landing --json
"""

import argparse
import json
import sys
from typing import Any

from url_utils import validate_url

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Error: playwright required. Install with: pip install -r requirements.txt && playwright install chromium")
    sys.exit(1)


def analyze_landing(url: str, timeout: int = 30000) -> dict[str, Any]:
    """
    Analyze landing page quality for ad campaign relevance.

    Checks:
        - Core Web Vitals (LCP, CLS) for G59 (mobile speed)
        - H1/title for G60 (landing page relevance)
        - Schema markup for G61 (structured data)
        - Mobile responsiveness
        - CTA visibility above fold
        - Form presence and field count
        - Trust signals (testimonials, badges, reviews)
    """
    result = {
        "url": url,
        "performance": {
            "lcp_ms": None,
            "cls": None,
            "ttfb_ms": None,
            "dom_content_loaded_ms": None,
        },
        "content": {
            "title": None,
            "h1": None,
            "meta_description": None,
            "word_count": 0,
        },
        "conversion": {
            "cta_above_fold": False,
            "form_present": False,
            "form_fields": 0,
            "phone_number": False,
            "chat_widget": False,
        },
        "trust": {
            "testimonials": False,
            "trust_badges": False,
            "reviews_schema": False,
        },
        "mobile": {
            "viewport_meta": False,
            "horizontal_scroll": False,
            "font_readable": True,
        },
        "schema": {
            "types_found": [],
            "product_schema": False,
            "faq_schema": False,
            "service_schema": False,
        },
        "error": None,
    }

    try:
        url = validate_url(url)
    except ValueError as e:
        result["error"] = str(e)
        return result

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # Desktop analysis
            desktop = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = desktop.new_page()

            page.goto(url, wait_until="networkidle", timeout=timeout)

            # Performance metrics
            perf = page.evaluate("""
                () => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    return {
                        ttfb: nav ? nav.responseStart : null,
                        domContentLoaded: nav ? nav.domContentLoadedEventEnd : null,
                    };
                }
            """)
            if perf.get("ttfb") is not None:
                result["performance"]["ttfb_ms"] = round(perf["ttfb"])
            if perf.get("domContentLoaded") is not None:
                result["performance"]["dom_content_loaded_ms"] = round(perf["domContentLoaded"])

            # CLS
            cls = page.evaluate("""
                () => new Promise(resolve => {
                    let clsValue = 0;
                    new PerformanceObserver(list => {
                        for (const entry of list.getEntries()) {
                            if (!entry.hadRecentInput) clsValue += entry.value;
                        }
                        resolve(clsValue);
                    }).observe({type: 'layout-shift', buffered: true});
                    setTimeout(() => resolve(clsValue), 3000);
                })
            """)
            result["performance"]["cls"] = round(cls, 4) if cls is not None else None

            # Content analysis
            result["content"]["title"] = page.title()

            h1 = page.query_selector("h1")
            if h1:
                result["content"]["h1"] = h1.text_content().strip()

            meta_desc = page.query_selector('meta[name="description"]')
            if meta_desc:
                result["content"]["meta_description"] = meta_desc.get_attribute("content")

            result["content"]["word_count"] = page.evaluate(
                "() => document.body.innerText.split(/\\s+/).filter(w => w.length > 0).length"
            )

            # CTA above fold
            cta_selectors = [
                "a[href*='signup']", "a[href*='register']", "a[href*='contact']",
                "a[href*='demo']", "a[href*='trial']", "a[href*='buy']",
                "button:has-text('Get Started')", "button:has-text('Sign Up')",
                "button:has-text('Buy Now')", "button:has-text('Contact')",
                "button:has-text('Free Trial')", "button:has-text('Book')",
                ".cta", "[class*='cta']",
            ]
            for selector in cta_selectors:
                try:
                    cta = page.query_selector(selector)
                    if cta:
                        box = cta.bounding_box()
                        if box and box["y"] < 1080:
                            result["conversion"]["cta_above_fold"] = True
                            break
                except Exception:
                    pass

            # Form analysis
            forms = page.query_selector_all("form")
            if forms:
                result["conversion"]["form_present"] = True
                inputs = page.query_selector_all("form input:not([type='hidden']):not([type='submit'])")
                result["conversion"]["form_fields"] = len(inputs)

            # Phone number
            result["conversion"]["phone_number"] = page.query_selector("a[href^='tel:']") is not None

            # Chat widget
            chat_selectors = [
                "[class*='chat']", "[id*='chat']", "[class*='intercom']",
                "[class*='drift']", "[class*='hubspot']", "[class*='zendesk']",
            ]
            for sel in chat_selectors:
                try:
                    if page.query_selector(sel):
                        result["conversion"]["chat_widget"] = True
                        break
                except Exception:
                    pass

            # Trust signals
            page_text = page.evaluate("() => document.body.innerText.toLowerCase()")
            result["trust"]["testimonials"] = any(k in page_text for k in ["testimonial", "customer said", "what our"])
            result["trust"]["trust_badges"] = any(k in page_text for k in ["trusted by", "as seen", "certified", "award"])

            # Schema markup
            schemas = page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    const types = [];
                    scripts.forEach(s => {
                        try {
                            const data = JSON.parse(s.textContent);
                            if (data['@type']) types.push(data['@type']);
                            if (Array.isArray(data['@graph'])) {
                                data['@graph'].forEach(item => { if (item['@type']) types.push(item['@type']); });
                            }
                        } catch(e) {}
                    });
                    return types;
                }
            """)
            result["schema"]["types_found"] = schemas
            result["schema"]["product_schema"] = "Product" in schemas
            result["schema"]["faq_schema"] = "FAQPage" in schemas
            result["schema"]["service_schema"] = "Service" in schemas
            result["trust"]["reviews_schema"] = "Review" in schemas or "AggregateRating" in schemas

            desktop.close()

            # Mobile analysis
            mobile = browser.new_context(viewport={"width": 375, "height": 812})
            page = mobile.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout)

            # LCP on mobile viewport (G59 = mobile speed)
            lcp = page.evaluate("""
                () => new Promise(resolve => {
                    new PerformanceObserver(list => {
                        const entries = list.getEntries();
                        resolve(entries.length > 0 ? entries[entries.length - 1].startTime : null);
                    }).observe({type: 'largest-contentful-paint', buffered: true});
                    setTimeout(() => resolve(null), 3000);
                })
            """)
            if lcp is not None:
                result["performance"]["lcp_ms"] = round(lcp)

            result["mobile"]["viewport_meta"] = page.query_selector('meta[name="viewport"]') is not None

            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            viewport_width = page.evaluate("window.innerWidth")
            result["mobile"]["horizontal_scroll"] = scroll_width > viewport_width

            base_font = page.evaluate(
                "() => parseFloat(window.getComputedStyle(document.body).fontSize)"
            )
            result["mobile"]["font_readable"] = base_font >= 16

            mobile.close()
            browser.close()

    except PlaywrightTimeout:
        result["error"] = f"Page load timed out after {timeout}ms"
    except Exception as e:
        result["error"] = str(e)

    return result


def grade_landing(result: dict[str, Any]) -> dict[str, str]:
    """Grade landing page quality based on ad audit criteria."""
    grades = {}

    # G59: Mobile speed (LCP)
    lcp = result["performance"].get("lcp_ms")
    if lcp is not None:
        if lcp < 2500:
            grades["G59_mobile_speed"] = "PASS"
        elif lcp < 4000:
            grades["G59_mobile_speed"] = "WARNING"
        else:
            grades["G59_mobile_speed"] = "FAIL"

    # G60: Landing page relevance (H1 present)
    grades["G60_relevance"] = "PASS" if result["content"]["h1"] else "FAIL"

    # G61: Schema markup (Product/FAQ/Service per google-audit.md)
    has_relevant_schema = (
        result["schema"]["product_schema"]
        or result["schema"]["faq_schema"]
        or result["schema"]["service_schema"]
    )
    grades["G61_schema"] = "PASS" if has_relevant_schema else "FAIL"

    # CTA above fold
    grades["cta_above_fold"] = "PASS" if result["conversion"]["cta_above_fold"] else "FAIL"

    # Mobile responsive
    has_viewport = result["mobile"]["viewport_meta"]
    no_scroll = not result["mobile"]["horizontal_scroll"]
    grades["mobile_responsive"] = "PASS" if has_viewport and no_scroll else "FAIL"

    # Form friction (for lead gen)
    if result["conversion"]["form_present"]:
        fields = result["conversion"]["form_fields"]
        if fields <= 5:
            grades["form_friction"] = "PASS"
        elif fields <= 8:
            grades["form_friction"] = "WARNING"
        else:
            grades["form_friction"] = "FAIL"

    return grades


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze landing page quality for ad campaigns")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--timeout", "-t", type=int, default=30000, help="Timeout in ms")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    result = analyze_landing(args.url, timeout=args.timeout)
    grades = grade_landing(result)

    if args.json:
        output = {**result, "grades": grades}
        print(json.dumps(output, indent=2))
    else:
        print("Landing Page Quality Analysis")
        print("=" * 50)
        print(f"\nURL: {result['url']}")

        print("\nPerformance:")
        lcp = result["performance"]["lcp_ms"]
        lcp_status = "GOOD" if lcp is not None and lcp < 2500 else "SLOW" if lcp is not None else "N/A"
        print(f"  LCP: {lcp}ms ({lcp_status})")
        cls = result["performance"]["cls"]
        cls_status = "GOOD" if cls is not None and cls < 0.1 else "POOR" if cls is not None else "N/A"
        print(f"  CLS: {cls} ({cls_status})")
        print(f"  TTFB: {result['performance']['ttfb_ms']}ms")

        print(f"\nContent:")
        print(f"  Title: {result['content']['title']}")
        print(f"  H1: {result['content']['h1'] or 'MISSING'}")
        print(f"  Words: {result['content']['word_count']}")

        print(f"\nConversion Elements:")
        print(f"  CTA Above Fold: {'Y' if result['conversion']['cta_above_fold'] else 'N'}")
        print(f"  Form: {'Y (' + str(result['conversion']['form_fields']) + ' fields)' if result['conversion']['form_present'] else 'N'}")
        print(f"  Phone: {'Y' if result['conversion']['phone_number'] else 'N'}")
        print(f"  Chat: {'Y' if result['conversion']['chat_widget'] else 'N'}")

        print(f"\nSchema: {', '.join(result['schema']['types_found']) or 'None'}")

        print(f"\nAudit Grades:")
        for check, grade in grades.items():
            print(f"  [{grade}] {check}")

        if result["error"]:
            print(f"\nError: {result['error']}")


if __name__ == "__main__":
    main()
