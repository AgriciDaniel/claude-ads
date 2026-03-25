"""Google Ads auditor -- evaluates account data against 20+ key checks.

Each check returns a dict:
  {check_id, category, name, severity, status, score, detail, fix, fix_time_minutes, is_quick_win}

Categories and weights (from the 74-check framework):
  Conversion Tracking  25%
  Wasted Spend         20%
  Account Structure    15%
  Keywords & QS        15%
  Ads & Assets         15%
  Settings & Targeting 10%
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from app.connectors.google_ads import GoogleAdsData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default


def _micros_to_currency(micros: int | float) -> float:
    return micros / 1_000_000


def _check(
    check_id: str,
    category: str,
    name: str,
    severity: str,
    status: str,
    score: int,
    detail: str,
    fix: str = "",
    fix_time_minutes: int = 0,
    is_quick_win: bool = False,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "category": category,
        "name": name,
        "severity": severity,
        "status": status,
        "score": score,
        "detail": detail,
        "fix": fix,
        "fix_time_minutes": fix_time_minutes,
        "is_quick_win": is_quick_win,
    }


# ---------------------------------------------------------------------------
# Category weights for final scoring
# ---------------------------------------------------------------------------

CATEGORY_WEIGHTS: dict[str, float] = {
    "Conversion Tracking": 0.25,
    "Wasted Spend": 0.20,
    "Account Structure": 0.15,
    "Keywords & Quality Score": 0.15,
    "Ads & Assets": 0.15,
    "Settings & Targeting": 0.10,
}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_g42_conversion_actions(data: GoogleAdsData) -> dict:
    """G42: Conversion actions defined."""
    primary = [
        ca for ca in data.conversion_actions
        if ca.get("conversion_action", {}).get("include_in_conversions_metric")
    ]
    if len(primary) >= 1:
        return _check("G42", "Conversion Tracking", "Conversion actions defined",
                       "critical", "pass", 100,
                       f"{len(primary)} primary conversion action(s) configured.")
    return _check("G42", "Conversion Tracking", "Conversion actions defined",
                   "critical", "fail", 0,
                   "No active primary conversion actions found.",
                   "Configure at least one primary conversion action in Google Ads.", 10)


def _check_g43_enhanced_conversions(data: GoogleAdsData) -> dict:
    """G43: Enhanced conversions enabled."""
    # Check if any conversion action has enhanced conversions type markers
    has_enhanced = any(
        "WEBPAGE" in str(ca.get("conversion_action", {}).get("type", ""))
        for ca in data.conversion_actions
    )
    if has_enhanced:
        return _check("G43", "Conversion Tracking", "Enhanced conversions enabled",
                       "critical", "pass", 100,
                       "Enhanced conversions detected.")
    return _check("G43", "Conversion Tracking", "Enhanced conversions enabled",
                   "critical", "fail", 0,
                   "Enhanced conversions not detected.",
                   "Enable Enhanced Conversions in Google Ads conversion settings.", 5,
                   is_quick_win=True)


def _check_g47_macro_micro_separation(data: GoogleAdsData) -> dict:
    """G47: Micro vs macro conversion separation."""
    primary_actions = [
        ca for ca in data.conversion_actions
        if ca.get("conversion_action", {}).get("include_in_conversions_metric")
    ]
    micro_categories = {"ADD_TO_CART", "PAGE_VIEW", "BEGIN_CHECKOUT", "OTHER"}
    micro_as_primary = [
        ca for ca in primary_actions
        if str(ca.get("conversion_action", {}).get("category", "")).upper()
        in micro_categories
    ]
    if not micro_as_primary:
        return _check("G47", "Conversion Tracking", "Micro vs macro separation",
                       "high", "pass", 100,
                       "Only macro conversions set as primary for bidding.")
    if len(micro_as_primary) <= 2:
        return _check("G47", "Conversion Tracking", "Micro vs macro separation",
                       "high", "warning", 50,
                       f"{len(micro_as_primary)} micro conversion(s) set as primary.",
                       "Set micro events (AddToCart, PageView) as secondary.", 5)
    return _check("G47", "Conversion Tracking", "Micro vs macro separation",
                   "high", "fail", 0,
                   f"{len(micro_as_primary)} micro conversions used as primary.",
                   "Only keep Purchase/Lead/SignUp as primary conversion actions.", 10)


def _check_g48_attribution_model(data: GoogleAdsData) -> dict:
    """G48: Attribution model -- data-driven preferred."""
    models = [
        str(ca.get("conversion_action", {})
            .get("attribution_model_settings", {})
            .get("attribution_model", ""))
        for ca in data.conversion_actions
    ]
    dda_count = sum(1 for m in models if "DATA_DRIVEN" in m.upper())
    if not models:
        return _check("G48", "Conversion Tracking", "Attribution model",
                       "medium", "na", 0, "No conversion actions to evaluate.")
    if dda_count == len(models):
        return _check("G48", "Conversion Tracking", "Attribution model",
                       "medium", "pass", 100,
                       "All conversion actions use data-driven attribution.")
    return _check("G48", "Conversion Tracking", "Attribution model",
                   "medium", "warning", 50,
                   f"{dda_count}/{len(models)} actions use data-driven attribution.",
                   "Switch remaining actions to data-driven attribution.", 5)


def _check_g14_negative_keyword_lists(data: GoogleAdsData) -> dict:
    """G14: Negative keyword lists exist."""
    count = len(data.negative_keyword_lists)
    if count >= 3:
        return _check("G14", "Wasted Spend", "Negative keyword lists exist",
                       "critical", "pass", 100,
                       f"{count} negative keyword list(s) found.")
    if count >= 1:
        return _check("G14", "Wasted Spend", "Negative keyword lists exist",
                       "critical", "warning", 50,
                       f"Only {count} negative keyword list(s). Recommend 3+ themed lists.",
                       "Create themed negative lists (Competitor, Jobs, Free, Irrelevant).",
                       10, is_quick_win=True)
    return _check("G14", "Wasted Spend", "Negative keyword lists exist",
                   "critical", "fail", 0,
                   "No negative keyword lists found.",
                   "Create initial themed negative keyword lists.", 10,
                   is_quick_win=True)


def _check_g16_wasted_spend(data: GoogleAdsData) -> dict:
    """G16: Wasted spend on irrelevant search terms."""
    if not data.search_terms:
        return _check("G16", "Wasted Spend", "Wasted spend on irrelevant terms",
                       "critical", "na", 0, "No search term data available.")
    total_cost = sum(
        r.get("metrics", {}).get("cost_micros", 0) for r in data.search_terms
    )
    # Terms with 0 conversions and cost > 0 are candidates for waste
    wasted_cost = sum(
        r.get("metrics", {}).get("cost_micros", 0)
        for r in data.search_terms
        if r.get("metrics", {}).get("conversions", 0) == 0
        and r.get("metrics", {}).get("clicks", 0) > 2
    )
    pct = _safe_div(wasted_cost, total_cost) * 100
    if pct < 5:
        return _check("G16", "Wasted Spend", "Wasted spend on irrelevant terms",
                       "critical", "pass", 100,
                       f"Estimated waste: {pct:.1f}% of search term spend.")
    if pct < 15:
        return _check("G16", "Wasted Spend", "Wasted spend on irrelevant terms",
                       "critical", "warning", 50,
                       f"Estimated waste: {pct:.1f}% of search term spend.",
                       "Review search terms and add negatives for irrelevant queries.", 15)
    return _check("G16", "Wasted Spend", "Wasted spend on irrelevant terms",
                   "critical", "fail", 0,
                   f"Estimated waste: {pct:.1f}% -- significant budget leakage.",
                   "Urgently review search terms report and build negative keyword lists.", 30)


def _check_g17_broad_match_pairing(data: GoogleAdsData) -> dict:
    """G17: Broad match keywords must pair with smart bidding."""
    broad_manual = [
        kw for kw in data.keywords
        if str(kw.get("ad_group_criterion", {}).get("keyword", {})
               .get("match_type", "")).upper() == "BROAD"
        and "MANUAL" in str(kw.get("campaign", {}).get("bidding_strategy_type", "")).upper()
    ]
    if not broad_manual:
        return _check("G17", "Wasted Spend", "Broad match + smart bidding pairing",
                       "critical", "pass", 100,
                       "No broad match keywords running on manual CPC.")
    return _check("G17", "Wasted Spend", "Broad match + smart bidding pairing",
                   "critical", "fail", 0,
                   f"{len(broad_manual)} broad match keyword(s) on manual CPC.",
                   "Switch to Smart Bidding or change match type to Exact/Phrase.",
                   5, is_quick_win=True)


def _check_gws1_zero_conversion_keywords(data: GoogleAdsData) -> dict:
    """G-WS1: Zero-conversion keywords with significant clicks."""
    zero_conv = [
        kw for kw in data.keywords
        if kw.get("metrics", {}).get("clicks", 0) > 100
        and kw.get("metrics", {}).get("conversions", 0) == 0
    ]
    if not zero_conv:
        return _check("G-WS1", "Wasted Spend", "Zero-conversion keywords",
                       "high", "pass", 100,
                       "No keywords with >100 clicks and 0 conversions.")
    if len(zero_conv) <= 3:
        return _check("G-WS1", "Wasted Spend", "Zero-conversion keywords",
                       "high", "warning", 50,
                       f"{len(zero_conv)} keyword(s) with >100 clicks and 0 conversions.",
                       "Review and pause or adjust these keywords.", 10)
    return _check("G-WS1", "Wasted Spend", "Zero-conversion keywords",
                   "high", "fail", 0,
                   f"{len(zero_conv)} keywords with >100 clicks and 0 conversions.",
                   "Pause non-converting keywords and reallocate budget.", 15)


def _check_g03_single_theme_ad_groups(data: GoogleAdsData) -> dict:
    """G03: Single theme ad groups (<=10 keywords per group)."""
    # Count keywords per ad group
    ag_keyword_count: Counter = Counter()
    for kw in data.keywords:
        ag_id = kw.get("ad_group", {}).get("id")
        if ag_id:
            ag_keyword_count[ag_id] += 1

    if not ag_keyword_count:
        return _check("G03", "Account Structure", "Single theme ad groups",
                       "high", "na", 0, "No keyword data to evaluate.")

    bloated = [ag for ag, cnt in ag_keyword_count.items() if cnt > 20]
    if not bloated:
        return _check("G03", "Account Structure", "Single theme ad groups",
                       "high", "pass", 100,
                       "All ad groups have 20 or fewer keywords.")
    pct = len(bloated) / len(ag_keyword_count) * 100
    if pct < 20:
        return _check("G03", "Account Structure", "Single theme ad groups",
                       "high", "warning", 60,
                       f"{len(bloated)} ad group(s) have >20 keywords ({pct:.0f}%).",
                       "Split large ad groups into tighter keyword themes.", 20)
    return _check("G03", "Account Structure", "Single theme ad groups",
                   "high", "fail", 20,
                   f"{len(bloated)} ad group(s) with >20 keywords ({pct:.0f}%).",
                   "Restructure into tightly themed ad groups (max 10-15 keywords).", 30)


def _check_g04_campaign_count(data: GoogleAdsData) -> dict:
    """G04: Campaign count -- not excessively fragmented."""
    active = [c for c in data.campaigns
              if str(c.get("campaign", {}).get("status", "")).upper() == "ENABLED"]
    count = len(active)
    if count <= 15:
        return _check("G04", "Account Structure", "Campaign count",
                       "high", "pass", 100,
                       f"{count} active campaigns -- well organized.")
    if count <= 25:
        return _check("G04", "Account Structure", "Campaign count",
                       "high", "warning", 60,
                       f"{count} active campaigns -- consider consolidation.",
                       "Review if campaigns can be merged by objective.", 20)
    return _check("G04", "Account Structure", "Campaign count",
                   "high", "fail", 20,
                   f"{count} active campaigns -- highly fragmented.",
                   "Consolidate campaigns. Fewer campaigns with adequate budget perform better.", 30)


def _check_g12_network_settings(data: GoogleAdsData) -> dict:
    """G12: Display Network disabled for Search campaigns."""
    search_campaigns = [
        c for c in data.campaigns
        if "SEARCH" in str(c.get("campaign", {}).get("advertising_channel_type", "")).upper()
    ]
    display_on = [
        c for c in search_campaigns
        if c.get("campaign", {}).get("network_settings", {}).get("target_content_network")
    ]
    if not display_on:
        return _check("G12", "Account Structure", "Network settings",
                       "high", "pass", 100,
                       "Display Network disabled on all Search campaigns.")
    return _check("G12", "Account Structure", "Network settings",
                   "high", "fail", 0,
                   f"{len(display_on)} Search campaign(s) have Display Network enabled.",
                   "Disable Display Network on Search campaigns.", 2,
                   is_quick_win=True)


def _check_g11_geo_targeting(data: GoogleAdsData) -> dict:
    """G11: Geographic targeting accuracy -- 'People in' preferred."""
    bad_geo = [
        c for c in data.campaigns
        if "PRESENCE_OR_INTEREST" in str(
            c.get("campaign", {}).get("geo_target_type_setting", {})
            .get("positive_geo_target_type", "")
        ).upper()
    ]
    if not bad_geo:
        return _check("G11", "Account Structure", "Geographic targeting accuracy",
                       "high", "pass", 100,
                       "All campaigns use 'People in' targeting.")
    return _check("G11", "Account Structure", "Geographic targeting accuracy",
                   "high", "fail", 0,
                   f"{len(bad_geo)} campaign(s) use 'People in or interested in'.",
                   "Switch to 'People in' your targeted locations.", 2,
                   is_quick_win=True)


def _check_g20_avg_quality_score(data: GoogleAdsData) -> dict:
    """G20: Average Quality Score (impression-weighted)."""
    total_impressions = 0
    weighted_qs = 0
    scored = 0
    for kw in data.keywords:
        qs = kw.get("ad_group_criterion", {}).get("quality_info", {}).get("quality_score")
        imps = kw.get("metrics", {}).get("impressions", 0)
        if qs and qs > 0 and imps > 0:
            weighted_qs += qs * imps
            total_impressions += imps
            scored += 1

    if not scored:
        return _check("G20", "Keywords & Quality Score", "Average Quality Score",
                       "high", "na", 0, "No keywords with Quality Score data.")

    avg_qs = _safe_div(weighted_qs, total_impressions)
    if avg_qs >= 7:
        return _check("G20", "Keywords & Quality Score", "Average Quality Score",
                       "high", "pass", 100,
                       f"Impression-weighted QS: {avg_qs:.1f} (target: 7+).")
    if avg_qs >= 5:
        return _check("G20", "Keywords & Quality Score", "Average Quality Score",
                       "high", "warning", 50,
                       f"Impression-weighted QS: {avg_qs:.1f} -- room for improvement.",
                       "Improve ad relevance and landing page experience for low-QS keywords.", 20)
    return _check("G20", "Keywords & Quality Score", "Average Quality Score",
                   "high", "fail", 10,
                   f"Impression-weighted QS: {avg_qs:.1f} -- critically low.",
                   "Restructure ad groups, improve ad copy relevance, optimize landing pages.", 30)


def _check_g21_critical_qs_keywords(data: GoogleAdsData) -> dict:
    """G21: Percentage of keywords with QS <= 3."""
    scored_kws = [
        kw for kw in data.keywords
        if kw.get("ad_group_criterion", {}).get("quality_info", {}).get("quality_score")
        and kw["ad_group_criterion"]["quality_info"]["quality_score"] > 0
    ]
    if not scored_kws:
        return _check("G21", "Keywords & Quality Score", "Critical QS keywords",
                       "critical", "na", 0, "No QS data available.")

    low_qs = [kw for kw in scored_kws
              if kw["ad_group_criterion"]["quality_info"]["quality_score"] <= 3]
    pct = len(low_qs) / len(scored_kws) * 100
    if pct < 10:
        return _check("G21", "Keywords & Quality Score", "Critical QS keywords",
                       "critical", "pass", 100,
                       f"{pct:.0f}% of keywords have QS <= 3.")
    if pct < 25:
        return _check("G21", "Keywords & Quality Score", "Critical QS keywords",
                       "critical", "warning", 50,
                       f"{pct:.0f}% of keywords have QS <= 3.",
                       "Review and improve or pause keywords with QS 1-3.", 15)
    return _check("G21", "Keywords & Quality Score", "Critical QS keywords",
                   "critical", "fail", 0,
                   f"{pct:.0f}% of keywords have QS <= 3 -- major issue.",
                   "Overhaul ad group themes, ad copy, and landing pages.", 30)


def _check_gkw1_zero_impression_keywords(data: GoogleAdsData) -> dict:
    """G-KW1: Zero-impression keywords in last 30 days."""
    active_kws = [
        kw for kw in data.keywords
        if str(kw.get("ad_group_criterion", {}).get("status", "")).upper() == "ENABLED"
    ]
    if not active_kws:
        return _check("G-KW1", "Keywords & Quality Score", "Zero-impression keywords",
                       "medium", "na", 0, "No active keywords to evaluate.")

    zero_imp = [kw for kw in active_kws
                if kw.get("metrics", {}).get("impressions", 0) == 0]
    pct = len(zero_imp) / len(active_kws) * 100
    if pct < 5:
        return _check("G-KW1", "Keywords & Quality Score", "Zero-impression keywords",
                       "medium", "pass", 100,
                       f"{pct:.0f}% of active keywords have 0 impressions.")
    if pct < 10:
        return _check("G-KW1", "Keywords & Quality Score", "Zero-impression keywords",
                       "medium", "warning", 60,
                       f"{pct:.0f}% of active keywords have 0 impressions.",
                       "Review zero-impression keywords for relevance or bid issues.", 10)
    return _check("G-KW1", "Keywords & Quality Score", "Zero-impression keywords",
                   "medium", "fail", 20,
                   f"{pct:.0f}% of active keywords have 0 impressions.",
                   "Remove or adjust keywords that are not generating impressions.", 15)


def _check_g26_rsa_per_ad_group(data: GoogleAdsData) -> dict:
    """G26: At least 1 RSA per ad group."""
    # Get active ad groups
    active_ag_ids = {
        ag.get("ad_group", {}).get("id")
        for ag in data.ad_groups
        if str(ag.get("ad_group", {}).get("status", "")).upper() == "ENABLED"
    }
    # RSAs by ad group
    rsa_ag_ids = {
        ad.get("ad_group", {}).get("id")
        for ad in data.ads
        if "RESPONSIVE_SEARCH" in str(ad.get("ad_group_ad", {}).get("ad", {}).get("type", "")).upper()
    }
    missing = active_ag_ids - rsa_ag_ids
    if not active_ag_ids:
        return _check("G26", "Ads & Assets", "RSA per ad group",
                       "high", "na", 0, "No active ad groups found.")
    if not missing:
        return _check("G26", "Ads & Assets", "RSA per ad group",
                       "high", "pass", 100,
                       "All active ad groups have at least one RSA.")
    pct = len(missing) / len(active_ag_ids) * 100
    return _check("G26", "Ads & Assets", "RSA per ad group",
                   "high", "fail", max(0, int(100 - pct)),
                   f"{len(missing)} ad group(s) ({pct:.0f}%) lack an RSA.",
                   "Create at least one RSA for each ad group.", 15)


def _check_g29_rsa_ad_strength(data: GoogleAdsData) -> dict:
    """G29: RSA Ad Strength -- Good or Excellent."""
    rsas = [
        ad for ad in data.ads
        if "RESPONSIVE_SEARCH" in str(ad.get("ad_group_ad", {}).get("ad", {}).get("type", "")).upper()
    ]
    if not rsas:
        return _check("G29", "Ads & Assets", "RSA Ad Strength",
                       "high", "na", 0, "No RSAs found.")

    poor = [ad for ad in rsas
            if "POOR" in str(ad.get("ad_group_ad", {}).get("ad_strength", "")).upper()]
    avg = [ad for ad in rsas
           if "AVERAGE" in str(ad.get("ad_group_ad", {}).get("ad_strength", "")).upper()]

    if poor:
        return _check("G29", "Ads & Assets", "RSA Ad Strength",
                       "high", "fail", 20,
                       f"{len(poor)} RSA(s) with 'Poor' ad strength.",
                       "Add more unique headlines/descriptions, reduce pinning.", 15)
    if avg:
        return _check("G29", "Ads & Assets", "RSA Ad Strength",
                       "high", "warning", 60,
                       f"{len(avg)} RSA(s) with 'Average' ad strength.",
                       "Diversify headlines and descriptions to reach 'Good' or better.", 10)
    return _check("G29", "Ads & Assets", "RSA Ad Strength",
                   "high", "pass", 100,
                   "All RSAs have 'Good' or 'Excellent' ad strength.")


def _check_g27_rsa_headline_count(data: GoogleAdsData) -> dict:
    """G27: RSA headline count -- at least 8 unique per RSA."""
    rsas = [
        ad for ad in data.ads
        if "RESPONSIVE_SEARCH" in str(ad.get("ad_group_ad", {}).get("ad", {}).get("type", "")).upper()
    ]
    if not rsas:
        return _check("G27", "Ads & Assets", "RSA headline count",
                       "high", "na", 0, "No RSAs found.")

    low_headline = []
    for ad in rsas:
        headlines = ad.get("ad_group_ad", {}).get("ad", {}).get(
            "responsive_search_ad", {}
        ).get("headlines", [])
        if len(headlines) < 8:
            low_headline.append(ad)

    if not low_headline:
        return _check("G27", "Ads & Assets", "RSA headline count",
                       "high", "pass", 100,
                       "All RSAs have 8+ headlines.")
    if all(
        len(ad.get("ad_group_ad", {}).get("ad", {}).get("responsive_search_ad", {}).get("headlines", []))
        >= 3 for ad in low_headline
    ):
        return _check("G27", "Ads & Assets", "RSA headline count",
                       "high", "warning", 50,
                       f"{len(low_headline)} RSA(s) have fewer than 8 headlines.",
                       "Add more unique headlines (target 12-15 per RSA).", 10)
    return _check("G27", "Ads & Assets", "RSA headline count",
                   "high", "fail", 20,
                   f"{len(low_headline)} RSA(s) have fewer than 3 headlines.",
                   "Add at least 8 unique headlines per RSA.", 15)


def _check_g50_sitelinks(data: GoogleAdsData) -> dict:
    """G50: Sitelink extensions -- at least 4 per campaign."""
    sitelinks_by_campaign: Counter = Counter()
    for ext in data.extensions:
        if "SITELINK" in str(ext.get("asset", {}).get("type", "")).upper():
            camp_id = ext.get("campaign", {}).get("id")
            if camp_id:
                sitelinks_by_campaign[camp_id] += 1

    active_campaigns = [
        c for c in data.campaigns
        if str(c.get("campaign", {}).get("status", "")).upper() == "ENABLED"
    ]
    if not active_campaigns:
        return _check("G50", "Settings & Targeting", "Sitelink extensions",
                       "high", "na", 0, "No active campaigns.")

    missing = [
        c for c in active_campaigns
        if sitelinks_by_campaign.get(c.get("campaign", {}).get("id"), 0) < 4
    ]
    if not missing:
        return _check("G50", "Settings & Targeting", "Sitelink extensions",
                       "high", "pass", 100,
                       "All active campaigns have 4+ sitelinks.")
    return _check("G50", "Settings & Targeting", "Sitelink extensions",
                   "high", "fail", max(0, int(100 - len(missing) / len(active_campaigns) * 100)),
                   f"{len(missing)} campaign(s) have fewer than 4 sitelinks.",
                   "Add at least 4 sitelinks to each campaign.", 10,
                   is_quick_win=True)


def _check_g56_audience_segments(data: GoogleAdsData) -> dict:
    """G56: Audience segments applied."""
    if data.audience_segments:
        return _check("G56", "Settings & Targeting", "Audience segments applied",
                       "high", "pass", 100,
                       f"{len(data.audience_segments)} audience segment(s) applied.")
    return _check("G56", "Settings & Targeting", "Audience segments applied",
                   "high", "fail", 0,
                   "No audience segments applied to any campaign.",
                   "Add remarketing and in-market audiences in Observation mode.", 10)


def _check_g57_customer_match(data: GoogleAdsData) -> dict:
    """G57: Customer Match lists uploaded."""
    if data.customer_match_lists:
        return _check("G57", "Settings & Targeting", "Customer Match lists",
                       "high", "pass", 100,
                       f"{len(data.customer_match_lists)} Customer Match list(s) found.")
    return _check("G57", "Settings & Targeting", "Customer Match lists",
                   "high", "fail", 0,
                   "No Customer Match lists found.",
                   "Upload a Customer Match list for better audience targeting.", 15)


def _check_g36_smart_bidding(data: GoogleAdsData) -> dict:
    """G36: Smart bidding strategy active for eligible campaigns."""
    active_campaigns = [
        c for c in data.campaigns
        if str(c.get("campaign", {}).get("status", "")).upper() == "ENABLED"
    ]
    manual = [
        c for c in active_campaigns
        if "MANUAL" in str(c.get("campaign", {}).get("bidding_strategy_type", "")).upper()
        and c.get("metrics", {}).get("conversions", 0) >= 15
    ]
    if not manual:
        return _check("G36", "Settings & Targeting", "Smart bidding strategy",
                       "high", "pass", 100,
                       "All eligible campaigns use automated bidding.")
    return _check("G36", "Settings & Targeting", "Smart bidding strategy",
                   "high", "fail", 20,
                   f"{len(manual)} campaign(s) with 15+ conversions still use manual CPC.",
                   "Switch to Target CPA, Target ROAS, or Maximize Conversions.", 10)


def _check_g08_budget_allocation(data: GoogleAdsData) -> dict:
    """G08: Budget allocation matches priority -- top performers not limited."""
    active = [
        c for c in data.campaigns
        if str(c.get("campaign", {}).get("status", "")).upper() == "ENABLED"
    ]
    limited = [
        c for c in active
        if c.get("campaign_budget", {}).get("has_recommended_budget")
        and c.get("metrics", {}).get("conversions", 0) > 0
    ]
    if not limited:
        return _check("G08", "Account Structure", "Budget allocation matches priority",
                       "high", "pass", 100,
                       "No converting campaigns are budget-limited.")
    return _check("G08", "Account Structure", "Budget allocation matches priority",
                   "high", "warning", 40,
                   f"{len(limited)} converting campaign(s) are budget-limited.",
                   "Increase budget for top-performing campaigns or reallocate from underperformers.", 10)


# ---------------------------------------------------------------------------
# Main auditor entry point
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    _check_g42_conversion_actions,
    _check_g43_enhanced_conversions,
    _check_g47_macro_micro_separation,
    _check_g48_attribution_model,
    _check_g14_negative_keyword_lists,
    _check_g16_wasted_spend,
    _check_g17_broad_match_pairing,
    _check_gws1_zero_conversion_keywords,
    _check_g03_single_theme_ad_groups,
    _check_g04_campaign_count,
    _check_g08_budget_allocation,
    _check_g11_geo_targeting,
    _check_g12_network_settings,
    _check_g20_avg_quality_score,
    _check_g21_critical_qs_keywords,
    _check_gkw1_zero_impression_keywords,
    _check_g26_rsa_per_ad_group,
    _check_g27_rsa_headline_count,
    _check_g29_rsa_ad_strength,
    _check_g50_sitelinks,
    _check_g56_audience_segments,
    _check_g57_customer_match,
    _check_g36_smart_bidding,
]


@dataclass
class AuditResult:
    """Aggregated audit result with overall score, grade, and per-check details."""

    score: float
    grade: str
    summary: str
    category_scores: list[dict[str, Any]]
    check_results: list[dict[str, Any]]


def _compute_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def run_audit(data: GoogleAdsData) -> AuditResult:
    """Run all checks against the fetched Google Ads data.

    Returns an AuditResult with overall score, grade, and per-check details.
    """
    results: list[dict[str, Any]] = []
    for check_fn in ALL_CHECKS:
        try:
            result = check_fn(data)
            results.append(result)
        except Exception as exc:
            # If a check crashes, record it as N/A
            results.append(_check(
                check_fn.__name__.replace("_check_", "").upper(),
                "Unknown",
                check_fn.__doc__ or check_fn.__name__,
                "medium", "na", 0,
                f"Check failed with error: {exc}",
            ))

    # Compute per-category scores
    cat_scores: dict[str, list[int]] = defaultdict(list)
    cat_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"pass": 0, "warning": 0, "fail": 0, "na": 0}
    )
    for r in results:
        cat = r["category"]
        if r["status"] != "na":
            cat_scores[cat].append(r["score"])
        cat_counts[cat][r["status"]] += 1

    category_results: list[dict[str, Any]] = []
    weighted_total = 0.0
    total_weight = 0.0
    for cat, weight in CATEGORY_WEIGHTS.items():
        scores = cat_scores.get(cat, [])
        avg = sum(scores) / len(scores) if scores else 0.0
        counts = cat_counts.get(cat, {"pass": 0, "warning": 0, "fail": 0, "na": 0})
        category_results.append({
            "category": cat,
            "score": round(avg, 1),
            "weight": weight,
            "check_count": sum(counts.values()),
            "pass_count": counts["pass"],
            "warn_count": counts["warning"],
            "fail_count": counts["fail"],
        })
        if scores:
            weighted_total += avg * weight
            total_weight += weight

    overall = round(weighted_total / total_weight, 1) if total_weight else 0.0
    grade = _compute_grade(overall)

    # Build summary
    fail_count = sum(1 for r in results if r["status"] == "fail")
    warn_count = sum(1 for r in results if r["status"] == "warning")
    quick_wins = [r for r in results if r.get("is_quick_win")]
    summary = (
        f"Overall Score: {overall}/100 (Grade: {grade}). "
        f"{fail_count} failing check(s), {warn_count} warning(s). "
        f"{len(quick_wins)} quick win(s) identified."
    )

    return AuditResult(
        score=overall,
        grade=grade,
        summary=summary,
        category_scores=category_results,
        check_results=results,
    )
