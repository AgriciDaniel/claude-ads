"""Versioned, source-grounded native report projections.

The profiles describe exact report fields, their normalized meaning, and the
context a caller must bind.  They intentionally do not guess localized Ads
Manager labels or coerce structurally different conversion metrics into one
cross-platform definition.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

ProfileStatus = Literal["fixture-verified", "disabled"]
Transform = Literal[
    "text",
    "lower_text",
    "linkedin_campaign_urn",
    "iso_date",
    "iso_datetime_date",
    "decimal",
    "micros",
]


@dataclass(frozen=True)
class NativeFieldMapping:
    """One exact source field and its normalized semantic."""

    source: str
    target: str
    transform: Transform
    semantic: str


@dataclass(frozen=True)
class NativeValueGuard:
    """A source-field invariant required to keep platform attribution honest."""

    source: str
    allowed_values: tuple[str, ...] = ()
    forbidden_values: tuple[str, ...] = ()
    semantic: str = ""


@dataclass(frozen=True)
class NativeDateCheck:
    """Relationship between two parsed report dates."""

    left_target: str
    right_target: str
    relation: Literal["same_date", "next_calendar_date"]
    semantic: str


@dataclass(frozen=True)
class NativeExportProfile:
    """Immutable native-report mapping contract for one platform."""

    schema_version: Literal["1.0.0"]
    profile_id: str
    platform: str
    status: ProfileStatus
    source_format: str
    report_grain: tuple[str, ...]
    fields: tuple[NativeFieldMapping, ...]
    guards: tuple[NativeValueGuard, ...]
    required_context: tuple[str, ...]
    conversion_action: str | None
    unsupported_normalized_fields: tuple[str, ...]
    source_ids: tuple[str, ...]
    source_urls: tuple[str, ...]
    disabled_reason: str | None = None
    date_checks: tuple[NativeDateCheck, ...] = ()

    @property
    def expected_headers(self) -> tuple[str, ...]:
        return tuple(item.source for item in self.fields) + tuple(item.source for item in self.guards)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic public capability description."""

        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "platform": self.platform,
            "status": self.status,
            "source_format": self.source_format,
            "report_grain": list(self.report_grain),
            "expected_headers": list(self.expected_headers),
            "fields": [asdict(item) for item in self.fields],
            "guards": [asdict(item) for item in self.guards],
            "date_checks": [asdict(item) for item in self.date_checks],
            "required_context": list(self.required_context),
            "conversion_action": self.conversion_action,
            "unsupported_normalized_fields": list(self.unsupported_normalized_fields),
            "source_ids": list(self.source_ids),
            "source_urls": list(self.source_urls),
            "disabled_reason": self.disabled_reason,
        }


def _field(source: str, target: str, transform: Transform, semantic: str) -> NativeFieldMapping:
    return NativeFieldMapping(source, target, transform, semantic)


_GOOGLE_FIELDS = (
    _field("segments.date", "date", "iso_date", "Daily segment in the Google Ads account time zone."),
    _field("customer.id", "account_id", "text", "Google Ads customer identifier."),
    _field("customer.descriptive_name", "account_name", "text", "Google Ads customer descriptive name."),
    _field("customer.currency_code", "currency", "text", "Google Ads customer ISO currency code."),
    _field("campaign.id", "campaign_id", "text", "Google Ads campaign identifier."),
    _field("campaign.name", "campaign_name", "text", "Google Ads campaign name."),
    _field("campaign.status", "campaign_status", "lower_text", "Google Ads campaign status enum."),
    _field("campaign_budget.amount_micros", "budget", "micros", "Campaign budget amount in micros; budget period remains native metadata."),
    _field("metrics.cost_micros", "spend", "micros", "Google Ads cost in millionths of account currency."),
    _field("metrics.conversions", "conversions", "decimal", "Conversions included in the Google Ads conversions metric for the query."),
)


PROFILES: dict[str, NativeExportProfile] = {
    "google": NativeExportProfile(
        "1.0.0",
        "google-ads-api-campaign-daily-v1",
        "google",
        "fixture-verified",
        "Google Ads API GAQL campaign-row CSV projection",
        ("date", "campaign_id"),
        _GOOGLE_FIELDS,
        (
            NativeValueGuard(
                "campaign.advertising_channel_type",
                forbidden_values=("VIDEO",),
                semantic="Dedicated VIDEO campaigns route to the YouTube profile, not the Google aggregate.",
            ),
        ),
        (),
        "google_ads_conversions_metric",
        ("creative_id", "creative_name"),
        ("google-ads-campaign-fields-official",),
        (
            "https://developers.google.com/google-ads/api/fields/latest/campaign",
            "https://developers.google.com/google-ads/api/fields/latest/ad_group_ad",
        ),
    ),
    "youtube": NativeExportProfile(
        "1.0.0",
        "youtube-google-ads-api-video-campaign-daily-v1",
        "youtube",
        "fixture-verified",
        "Google Ads API GAQL VIDEO campaign-row CSV projection",
        ("date", "campaign_id"),
        _GOOGLE_FIELDS,
        (
            NativeValueGuard(
                "campaign.advertising_channel_type",
                allowed_values=("VIDEO",),
                semantic="Only campaigns identified by Google Ads as VIDEO enter this dedicated YouTube profile.",
            ),
        ),
        (),
        "google_ads_conversions_metric",
        ("creative_id", "creative_name"),
        ("google-ads-campaign-fields-official", "youtube-google-ads-video-official"),
        (
            "https://developers.google.com/google-ads/api/docs/video/overview",
            "https://developers.google.com/google-ads/api/fields/latest/campaign",
        ),
    ),
    "meta": NativeExportProfile(
        "1.0.0",
        "meta-marketing-api-insights-campaign-daily-v1",
        "meta",
        "fixture-verified",
        "Meta Marketing API Insights campaign-row CSV projection",
        ("date", "campaign_id"),
        (
            _field("date_start", "date", "iso_date", "Start date of the daily Insights row."),
            _field("date_stop", "date_end", "iso_date", "End date of the daily Insights row."),
            _field("account_id", "account_id", "text", "Meta ad account identifier."),
            _field("campaign_id", "campaign_id", "text", "Meta campaign identifier."),
            _field("campaign_name", "campaign_name", "text", "Meta campaign name."),
            _field("spend", "spend", "decimal", "Amount spent in the ad account currency."),
        ),
        (),
        ("currency",),
        None,
        ("account_name", "campaign_status", "creative_id", "creative_name", "conversion_action", "conversions", "budget"),
        ("meta-insights-reporting-official",),
        ("https://developers.facebook.com/docs/marketing-api/insights/",),
        date_checks=(
            NativeDateCheck(
                "date",
                "date_end",
                "same_date",
                "The profile accepts only one-day Insights rows; date_start and date_stop must match.",
            ),
        ),
    ),
    "linkedin": NativeExportProfile(
        "1.0.0",
        "linkedin-ad-analytics-campaign-daily-v1",
        "linkedin",
        "fixture-verified",
        "LinkedIn adAnalytics response row flattened by documented JSON path",
        ("date", "campaign_id"),
        (
            _field("dateRange.start", "date", "iso_date", "UTC start date of the daily adAnalytics row."),
            _field("dateRange.end", "date_end", "iso_date", "UTC end date of the daily adAnalytics row."),
            _field(
                "pivotValues.0",
                "campaign_id",
                "linkedin_campaign_urn",
                "Campaign URN returned by a CAMPAIGN pivot.",
            ),
            _field("costInLocalCurrency", "spend", "decimal", "Cost in the sponsored account local currency."),
            _field("externalWebsiteConversions", "conversions", "decimal", "LinkedIn external website conversions metric."),
        ),
        (),
        ("account_id", "currency"),
        "external_website_conversions",
        ("account_name", "campaign_name", "campaign_status", "creative_id", "creative_name", "budget"),
        ("linkedin-ad-analytics-reporting-official",),
        ("https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting",),
        date_checks=(
            NativeDateCheck(
                "date",
                "date_end",
                "same_date",
                "A DAILY adAnalytics row has the same inclusive start and end date.",
            ),
        ),
    ),
    "tiktok": NativeExportProfile(
        "1.0.0",
        "tiktok-integrated-report-ad-daily-v1",
        "tiktok",
        "fixture-verified",
        "TikTok API for Business integrated AUCTION_AD report CSV projection",
        ("date", "campaign_id", "creative_id"),
        (
            _field("stat_time_day", "date", "iso_date", "Daily reporting dimension in the requested report time zone."),
            _field("advertiser_id", "account_id", "text", "TikTok advertiser identifier."),
            _field("campaign_id", "campaign_id", "text", "TikTok campaign identifier."),
            _field("campaign_name", "campaign_name", "text", "TikTok campaign name."),
            _field(
                "ad_id_v2",
                "creative_id",
                "text",
                "TikTok ad identifier across Manual Ads, Smart+ Campaigns, and Upgraded Smart+ Ads.",
            ),
            _field("ad_name", "creative_name", "text", "TikTok ad name."),
            _field("spend", "spend", "decimal", "TikTok total ad spend metric."),
            _field("conversion", "conversions", "decimal", "Conversions for the selected optimization event."),
        ),
        (),
        ("currency",),
        "selected_optimization_event",
        ("account_name", "campaign_status", "budget"),
        ("tiktok-integrated-reporting-official",),
        ("https://business-api.tiktok.com/portal/docs?id=1751087777884161",),
    ),
    "microsoft": NativeExportProfile(
        "1.0.0",
        "microsoft-ad-performance-daily-csv-v1",
        "microsoft",
        "fixture-verified",
        "Microsoft Advertising v13 AdPerformanceReport CSV, Daily aggregation",
        ("date", "campaign_id", "creative_id"),
        (
            _field("TimePeriod", "date", "iso_date", "Daily report period formatted yyyy-mm-dd."),
            _field("AccountId", "account_id", "text", "Microsoft Advertising account identifier."),
            _field("AccountName", "account_name", "text", "Microsoft Advertising account name."),
            _field("CampaignId", "campaign_id", "text", "Microsoft Advertising campaign identifier."),
            _field("CampaignName", "campaign_name", "text", "Microsoft Advertising campaign name."),
            _field("CampaignStatus", "campaign_status", "lower_text", "Microsoft Advertising campaign status."),
            _field("AdId", "creative_id", "text", "Microsoft Advertising ad identifier."),
            _field("AdTitle", "creative_name", "text", "Ad title used only as a display label, not a stable identity."),
            _field("ConversionsQualified", "conversions", "decimal", "Bidding-qualified conversions; the legacy Conversions column is deprecated and returns zero."),
            _field("Spend", "spend", "decimal", "Spend in the reported CurrencyCode."),
            _field("CurrencyCode", "currency", "text", "Report currency code."),
        ),
        (),
        (),
        "bidding_qualified_conversions",
        ("budget",),
        ("microsoft-ad-performance-report-official",),
        (
            "https://learn.microsoft.com/en-us/advertising/reporting-service/adperformancereportcolumn?view=bingads-13",
            "https://learn.microsoft.com/en-us/advertising/guides/reports?view=bingads-13",
        ),
    ),
    "apple": NativeExportProfile(
        "1.0.0",
        "apple-ads-api-v5-campaign-daily-v1",
        "apple",
        "fixture-verified",
        "Apple Ads API v5 campaign report row flattened by documented JSON path",
        ("date", "campaign_id"),
        (
            _field("granularity.date", "date", "iso_date", "Date in a DAILY campaign report granularity row."),
            _field("metadata.orgId", "account_id", "text", "Apple Ads organization identifier."),
            _field("metadata.campaignId", "campaign_id", "text", "Apple Ads campaign identifier."),
            _field("metadata.campaignName", "campaign_name", "text", "Apple Ads campaign name."),
            _field("metadata.campaignStatus", "campaign_status", "lower_text", "User-controlled Apple Ads campaign status."),
            _field("metadata.dailyBudgetAmount.amount", "budget", "decimal", "Campaign daily budget amount."),
            _field("total.localSpend.amount", "spend", "decimal", "Local spend amount for the daily row."),
            _field("total.localSpend.currency", "currency", "text", "Currency attached to local spend."),
            _field("total.totalInstalls", "conversions", "decimal", "Apple Ads total installs metric."),
        ),
        (),
        (),
        "total_installs",
        ("account_name", "creative_id", "creative_name"),
        ("apple-campaign-reporting-official",),
        (
            "https://developer.apple.com/documentation/apple_ads/get-campaign-level-reports",
            "https://developer.apple.com/documentation/apple_ads/reportingcampaign",
        ),
    ),
    "amazon": NativeExportProfile(
        "1.0.0",
        "amazon-native-report-unmapped-v1",
        "amazon",
        "disabled",
        "Amazon Ads native report",
        (),
        (),
        (),
        (),
        None,
        ("date", "account_id", "account_name", "currency", "campaign_id", "campaign_name", "campaign_status", "creative_id", "creative_name", "conversion_action", "conversions", "budget", "spend"),
        ("amazon-ads-api-official",),
        ("https://advertising.amazon.com/about-api/",),
        "The curated official source proves reporting availability but not a stable cross-product native field schema; profile selection must name an ad product and official report type first.",
    ),
    "reddit": NativeExportProfile(
        "1.0.0",
        "reddit-ads-api-v3-ad-daily-v1",
        "reddit",
        "fixture-verified",
        "Reddit Ads API v3 report CSV projection with DATE, CAMPAIGN_ID, and AD_ID breakdowns",
        ("date", "campaign_id", "creative_id"),
        (
            _field("DATE", "date", "iso_date", "Report date; Reddit defaults report metrics to UTC unless a time zone is requested."),
            _field("ACCOUNT_ID", "account_id", "text", "Reddit ad account identifier."),
            _field("CAMPAIGN_ID", "campaign_id", "text", "Reddit campaign identifier breakdown."),
            _field("AD_ID", "creative_id", "text", "Reddit ad identifier breakdown."),
            _field("SPEND", "spend", "micros", "Reddit SPEND divided by one million as required by the v3 report documentation."),
            _field("KEY_CONVERSION_TOTAL_COUNT", "conversions", "decimal", "Total count for the configured key conversion."),
        ),
        (),
        ("currency",),
        "key_conversion_total_count",
        ("account_name", "campaign_name", "campaign_status", "creative_name", "budget"),
        ("reddit-ads-reporting-v3-official",),
        ("https://ads-api.reddit.com/docs/v3/api/get-a-report",),
    ),
    "pinterest": NativeExportProfile(
        "1.0.0",
        "pinterest-campaign-analytics-daily-v1",
        "pinterest",
        "fixture-verified",
        "Pinterest campaign analytics CSV projection",
        ("date", "campaign_id"),
        (
            _field("DATE", "date", "iso_date", "Daily granularity date returned for the campaign analytics request."),
            _field("SPEND_IN_MICRO_DOLLAR", "spend", "micros", "Spend in millionths of advertiser currency."),
            _field("TOTAL_CONVERSIONS", "conversions", "decimal", "Total conversions for the requested reporting period and attribution settings."),
        ),
        (),
        ("account_id", "campaign_id", "currency"),
        "total_conversions",
        ("account_name", "campaign_name", "campaign_status", "creative_id", "creative_name", "budget"),
        ("pinterest-ads-reporting-official",),
        ("https://developers.pinterest.com/docs/analytics-and-reports/ads-reporting/",),
    ),
    "snapchat": NativeExportProfile(
        "1.0.0",
        "snap-campaign-stats-daily-v1",
        "snapchat",
        "fixture-verified",
        "Snap Marketing API campaign DAY stats row flattened by documented JSON path",
        ("date", "campaign_id"),
        (
            _field("start_time", "date", "iso_datetime_date", "Start date of the DAY timeseries row, retaining the report timezone's calendar date."),
            _field("end_time", "date_end", "iso_datetime_date", "Exclusive end date of the DAY timeseries row."),
            _field("id", "campaign_id", "text", "Campaign identifier from the campaign stats entity."),
            _field("stats.spend", "spend", "micros", "Snap spend in microcurrency."),
            _field("stats.conversion_purchases", "conversions", "decimal", "Attributed Snap purchase conversion count."),
        ),
        (),
        ("account_id", "currency"),
        "conversion_purchases",
        ("account_name", "campaign_name", "campaign_status", "creative_id", "creative_name", "budget"),
        ("snap-ads-measurement-official",),
        ("https://developers.snap.com/marketing-api/Ads-API/measurement",),
        date_checks=(
            NativeDateCheck(
                "date",
                "date_end",
                "next_calendar_date",
                "A DAY timeseries row ends on the following calendar date.",
            ),
        ),
    ),
    "x": NativeExportProfile(
        "1.0.0",
        "x-native-report-unmapped-v1",
        "x",
        "disabled",
        "X Ads native report",
        (),
        (),
        (),
        (),
        None,
        ("date", "account_id", "account_name", "currency", "campaign_id", "campaign_name", "campaign_status", "creative_id", "creative_name", "conversion_action", "conversions", "budget", "spend"),
        ("x-conversion-tracking",),
        ("https://business.x.com/en/help/campaign-measurement-and-analytics/conversion-tracking-for-websites/about-conversion-tracking",),
        "The curated X source covers website conversion tracking, not a current native reporting schema; accepting guessed report headers would be unsafe.",
    ),
}


def get_native_profile(platform: str) -> NativeExportProfile:
    """Return the sole v1 profile for a normalized platform name."""

    try:
        return PROFILES[platform.strip().lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported native export platform: {platform!r}") from exc
