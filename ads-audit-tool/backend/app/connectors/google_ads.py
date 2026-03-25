"""Google Ads API connector -- OAuth flow and GAQL data extraction.

Handles authentication and pulls all data needed for the 74-check audit
(G01-G61, G-CT1 to G-CT3, G-WS1, G-KW1, G-KW2, G-AD1, G-AD2, G-PM1 to G-PM5).
"""

from dataclasses import dataclass, field
from typing import Any

import httpx
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from app.config import settings


# ---------------------------------------------------------------------------
# GAQL queries -- one per data slice the auditor needs
# ---------------------------------------------------------------------------

QUERIES: dict[str, str] = {
    # -- Account Structure (G01-G12) ----------------------------------------
    "campaigns": """
        SELECT campaign.id,
               campaign.name,
               campaign.status,
               campaign.advertising_channel_type,
               campaign.advertising_channel_sub_type,
               campaign.bidding_strategy_type,
               campaign.target_cpa.target_cpa_micros,
               campaign.target_roas.target_roas,
               campaign_budget.amount_micros,
               campaign_budget.has_recommended_budget,
               campaign.network_settings.target_search_network,
               campaign.network_settings.target_content_network,
               campaign.geo_target_type_setting.positive_geo_target_type,
               campaign.start_date,
               metrics.impressions,
               metrics.clicks,
               metrics.cost_micros,
               metrics.conversions,
               metrics.conversions_value,
               metrics.all_conversions
        FROM campaign
        WHERE campaign.status != 'REMOVED'
          AND segments.date DURING LAST_30_DAYS
    """,

    "ad_groups": """
        SELECT ad_group.id,
               ad_group.name,
               ad_group.status,
               ad_group.type,
               campaign.id,
               campaign.name,
               metrics.impressions,
               metrics.clicks,
               metrics.cost_micros,
               metrics.conversions
        FROM ad_group
        WHERE ad_group.status != 'REMOVED'
          AND segments.date DURING LAST_30_DAYS
    """,

    # -- Wasted Spend / Negatives (G13-G19, G-WS1) -------------------------
    "search_terms": """
        SELECT search_term_view.search_term,
               search_term_view.status,
               campaign.id,
               campaign.name,
               ad_group.id,
               metrics.impressions,
               metrics.clicks,
               metrics.cost_micros,
               metrics.conversions
        FROM search_term_view
        WHERE segments.date DURING LAST_14_DAYS
    """,

    "negative_keyword_lists": """
        SELECT shared_set.id,
               shared_set.name,
               shared_set.type,
               shared_set.member_count
        FROM shared_set
        WHERE shared_set.type = 'NEGATIVE_KEYWORDS'
          AND shared_set.status = 'ENABLED'
    """,

    # -- Keywords & Quality Score (G20-G25, G-KW1, G-KW2) ------------------
    "keywords": """
        SELECT ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type,
               ad_group_criterion.quality_info.quality_score,
               ad_group_criterion.quality_info.creative_quality_score,
               ad_group_criterion.quality_info.post_click_quality_score,
               ad_group_criterion.quality_info.search_predicted_ctr,
               ad_group_criterion.status,
               ad_group.id,
               ad_group.name,
               campaign.id,
               campaign.name,
               campaign.bidding_strategy_type,
               metrics.impressions,
               metrics.clicks,
               metrics.cost_micros,
               metrics.conversions
        FROM keyword_view
        WHERE ad_group_criterion.status != 'REMOVED'
          AND segments.date DURING LAST_30_DAYS
    """,

    # -- Ads & Assets (G26-G35, G-AD1, G-AD2) ------------------------------
    "ads": """
        SELECT ad_group_ad.ad.id,
               ad_group_ad.ad.type,
               ad_group_ad.ad.responsive_search_ad.headlines,
               ad_group_ad.ad.responsive_search_ad.descriptions,
               ad_group_ad.ad_strength,
               ad_group_ad.status,
               ad_group.id,
               ad_group.name,
               campaign.id,
               metrics.impressions,
               metrics.clicks,
               metrics.cost_micros,
               metrics.ctr
        FROM ad_group_ad
        WHERE ad_group_ad.status != 'REMOVED'
          AND segments.date DURING LAST_30_DAYS
    """,

    # -- Performance Max (G-PM1 to G-PM5, G31-G34) -------------------------
    "asset_groups": """
        SELECT asset_group.id,
               asset_group.name,
               asset_group.status,
               asset_group.ad_strength,
               campaign.id,
               campaign.name
        FROM asset_group
        WHERE asset_group.status != 'REMOVED'
    """,

    "asset_group_assets": """
        SELECT asset_group_asset.asset,
               asset_group_asset.field_type,
               asset_group_asset.status,
               asset_group.id,
               campaign.id
        FROM asset_group_asset
    """,

    # -- Conversion Tracking (G42-G49, G-CT1 to G-CT3) ---------------------
    "conversion_actions": """
        SELECT conversion_action.id,
               conversion_action.name,
               conversion_action.type,
               conversion_action.status,
               conversion_action.category,
               conversion_action.counting_type,
               conversion_action.attribution_model_settings.attribution_model,
               conversion_action.click_through_lookback_window_days,
               conversion_action.include_in_conversions_metric
        FROM conversion_action
        WHERE conversion_action.status != 'REMOVED'
    """,

    # -- Settings & Targeting (G50-G61) -------------------------------------
    "extensions": """
        SELECT asset.id,
               asset.type,
               asset.name,
               asset.sitelink_asset.description1,
               asset.call_asset.phone_number,
               asset.callout_asset.callout_text,
               asset.structured_snippet_asset.header,
               campaign.id,
               campaign.name
        FROM campaign_asset
        WHERE campaign.status != 'REMOVED'
    """,

    "audience_segments": """
        SELECT campaign_criterion.campaign,
               campaign_criterion.type,
               campaign_criterion.status,
               campaign.id,
               campaign.name
        FROM campaign_criterion
        WHERE campaign_criterion.type IN ('USER_LIST', 'USER_INTEREST', 'CUSTOM_AUDIENCE')
    """,

    "customer_match_lists": """
        SELECT user_list.id,
               user_list.name,
               user_list.type,
               user_list.size_for_search,
               user_list.membership_status
        FROM user_list
        WHERE user_list.type = 'CRM_BASED'
    """,

    # -- Bidding & Budget (G36-G41) -----------------------------------------
    "bidding_strategies": """
        SELECT bidding_strategy.id,
               bidding_strategy.name,
               bidding_strategy.type,
               bidding_strategy.status,
               metrics.conversions,
               metrics.cost_micros
        FROM bidding_strategy
        WHERE bidding_strategy.status != 'REMOVED'
          AND segments.date DURING LAST_30_DAYS
    """,
}


@dataclass
class GoogleAdsData:
    """Container for all data pulled from the Google Ads API."""

    campaigns: list[dict[str, Any]] = field(default_factory=list)
    ad_groups: list[dict[str, Any]] = field(default_factory=list)
    search_terms: list[dict[str, Any]] = field(default_factory=list)
    negative_keyword_lists: list[dict[str, Any]] = field(default_factory=list)
    keywords: list[dict[str, Any]] = field(default_factory=list)
    ads: list[dict[str, Any]] = field(default_factory=list)
    asset_groups: list[dict[str, Any]] = field(default_factory=list)
    asset_group_assets: list[dict[str, Any]] = field(default_factory=list)
    conversion_actions: list[dict[str, Any]] = field(default_factory=list)
    extensions: list[dict[str, Any]] = field(default_factory=list)
    audience_segments: list[dict[str, Any]] = field(default_factory=list)
    customer_match_lists: list[dict[str, Any]] = field(default_factory=list)
    bidding_strategies: list[dict[str, Any]] = field(default_factory=list)


def _build_client(refresh_token: str) -> GoogleAdsClient:
    """Create a GoogleAdsClient from stored credentials."""
    config = {
        "developer_token": settings.google_ads_developer_token,
        "client_id": settings.google_ads_client_id,
        "client_secret": settings.google_ads_client_secret,
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }
    if settings.google_ads_login_customer_id:
        config["login_customer_id"] = settings.google_ads_login_customer_id
    return GoogleAdsClient.load_from_dict(config)


def _rows_to_dicts(response) -> list[dict[str, Any]]:
    """Convert a Google Ads API streaming response to a list of flat dicts."""
    rows: list[dict[str, Any]] = []
    for batch in response:
        for row in batch.results:
            rows.append(_proto_to_dict(row))
    return rows


def _proto_to_dict(proto_obj) -> dict[str, Any]:
    """Recursively convert a protobuf-plus message to a nested dict."""
    result: dict[str, Any] = {}
    for field_name in dir(proto_obj):
        if field_name.startswith("_"):
            continue
        try:
            value = getattr(proto_obj, field_name)
        except AttributeError:
            continue
        if callable(value):
            continue
        if hasattr(value, "DESCRIPTOR"):
            result[field_name] = _proto_to_dict(value)
        elif isinstance(value, (list, tuple)):
            result[field_name] = [
                _proto_to_dict(v) if hasattr(v, "DESCRIPTOR") else v
                for v in value
            ]
        else:
            result[field_name] = value
    return result


def fetch_account_data(customer_id: str, refresh_token: str) -> GoogleAdsData:
    """Pull all data needed for the 74-check audit.

    Args:
        customer_id: Google Ads customer ID (no dashes, e.g. "1234567890").
        refresh_token: OAuth2 refresh token for this account.

    Returns:
        GoogleAdsData with all query results populated.

    Raises:
        GoogleAdsException: If any API call fails.
    """
    client = _build_client(refresh_token)
    ga_service = client.get_service("GoogleAdsService")

    data = GoogleAdsData()

    for query_name, gaql in QUERIES.items():
        try:
            response = ga_service.search_stream(
                customer_id=customer_id, query=gaql.strip(),
            )
            rows = _rows_to_dicts(response)
            setattr(data, query_name, rows)
        except GoogleAdsException as ex:
            # Non-fatal: store empty list -- the auditor marks affected checks N/A
            print(
                f"Warning: query '{query_name}' failed: "
                f"{ex.failure.errors[0].message}"
            )
            setattr(data, query_name, [])

    return data


def get_oauth_authorize_url(state: str) -> str:
    """Generate the Google OAuth2 authorization URL for consent screen."""
    params = {
        "client_id": settings.google_ads_client_id,
        "redirect_uri": settings.google_ads_redirect_uri,
        "response_type": "code",
        "scope": (
            "https://www.googleapis.com/auth/adwords "
            "https://www.googleapis.com/auth/userinfo.email "
            "https://www.googleapis.com/auth/userinfo.profile"
        ),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{query}"


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange an authorization code for access + refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "redirect_uri": settings.google_ads_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an expired access token using the stored refresh token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_user_info(access_token: str) -> dict[str, Any]:
    """Fetch the authenticated user's Google profile info."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


def list_accessible_accounts(refresh_token: str) -> list[dict[str, str]]:
    """List all Google Ads accounts accessible via the given refresh token."""
    client = _build_client(refresh_token)
    customer_service = client.get_service("CustomerService")

    try:
        accessible = customer_service.list_accessible_customers()
        accounts: list[dict[str, str]] = []
        ga_service = client.get_service("GoogleAdsService")

        for resource_name in accessible.resource_names:
            customer_id = resource_name.split("/")[-1]
            try:
                query = """
                    SELECT customer.id,
                           customer.descriptive_name
                    FROM customer
                    LIMIT 1
                """
                response = ga_service.search_stream(
                    customer_id=customer_id, query=query.strip(),
                )
                for batch in response:
                    for row in batch.results:
                        accounts.append({
                            "customer_id": str(row.customer.id),
                            "account_name": row.customer.descriptive_name,
                        })
            except GoogleAdsException:
                # May not have access to read details for this account
                accounts.append({
                    "customer_id": customer_id,
                    "account_name": None,
                })
        return accounts
    except GoogleAdsException as ex:
        raise RuntimeError(
            f"Failed to list accounts: {ex.failure.errors[0].message}"
        ) from ex
