# Creative Specification Resolution

**Verified:** 2026-08-25
**Refresh due:** 2026-09-24
**Evidence status:** source index and validation workflow, not a universal spec sheet

Creative requirements vary by format, placement, objective, geography, account
eligibility, and product release. Resolve the exact format before validating an
asset. A single “platform spec” table is unsafe because it silently merges
requirements that do not apply to the same placement.

## Resolution order

1. Capture platform, objective, format, placement, destination, geography, and
   the current account UI selection.
2. Open the matching platform-specific creative reference.
3. Verify volatile limits against the current official help page or API schema.
4. Prefer the stricter requirement when an asset must serve across placements.
5. Preview in the account UI and validate the rendered crop, overlays, text,
   captions, audio, CTA, disclosure, and destination.
6. Record source ID, retrieval date, observed UI/API version, and exceptions.

If sources disagree, do not guess. Label the check `unknown`, preserve both
values, and request a current preview or API validation.

## Current source entry points

| Platform | First-party source | Scope |
| --- | --- | --- |
| Google / YouTube | `google-rsa-official` — [Responsive search ads](https://support.google.com/google-ads/answer/7684791) and [Google Ads asset requirements](https://support.google.com/adspolicy/answer/6368661) | Search text and general asset policy |
| Meta | `meta-video-ads-official`: [Meta Reels ads](https://www.facebook.com/business/ads/facebook-instagram-reels-ads) | Reels creative guidance and format discovery |
| LinkedIn | `linkedin-ads-guide-official`: [LinkedIn Ads Guide](https://business.linkedin.com/advertise/ads/ads-guide) | Current format entry points |
| TikTok | `tiktok-ad-format-policy-official`: [Ad format and functionality](https://ads.tiktok.com/resources/help/article/tiktok-ads-policy-ad-format-and-functionality) | Creative and editorial requirements |
| Microsoft | `microsoft-ad-types-official`: [ResponsiveSearchAd schema](https://learn.microsoft.com/en-us/advertising/campaign-management-service/responsivesearchad?view=bingads-13) | Current v13 responsive-search-ad behavior |
| Apple | `apple-ads-creative-official`: [Apple Ads resources](https://ads.apple.com/app-store/resources) | Apple Ads resources and creative entry points |
| Amazon | `amazon-creative-acceptance-official`: [General requirements](https://advertising.amazon.com/help/GDG2CCTRU55BYY2Y) | Amazon Ads general creative requirements |
| Reddit | `reddit-ads-help-official` — [Reddit Ads Help](https://business.reddithelp.com/s/) | Current Reddit help and policy discovery |
| Pinterest | `pinterest-ad-specs-official` — [Pinterest ad specs](https://help.pinterest.com/en/business/article/pinterest-product-specs) | Pinterest formats and assets |
| Snapchat | `snap-creative-specs-official` — [Snap creative specifications](https://forbusiness.snapchat.com/advertising/ad-formats) | Snap ad-format entry point |
| X | `x-creative-specs-official` — [X Ads creative specs](https://business.x.com/en/help/campaign-setup/creative-ad-specifications) | X formats and assets |

These pages are discovery points, not proof that every format is available in a
given account. Re-check the active UI/API before emitting a pass or a mutation.

## Precisely retained facts

Google's current responsive-search-ad documentation says an RSA can accept up to
15 headlines and four descriptions, and headline fields support up to 30
characters. Microsoft's current v13 schema says its RSA accepts three to 15
headlines and two to four descriptions. These facts apply only to those named formats;
they do not establish a cross-platform text standard.

## Validation output

For each asset return:

- `platform`, `format`, `placement`, `objective`, and `geography`.
- Observed dimensions, duration, file type, file size, text fields, audio,
  captions, destination, CTA, and disclosure.
- `pass`, `fail`, `unknown`, or `not_applicable` for each applicable requirement.
- Official source ID and retrieval date for every precise limit.
- Preview evidence and any crop or overlay risk.
- Remediation that preserves the creative concept.

## Non-universal rules

- There is no universal vertical-video safe zone. Validate against the current
  placement preview and platform overlay guidance.
- Recommended sizes are not always minimum acceptance requirements; label them.
- A platform upload success is not proof of policy approval or good rendering.
- Character counts may use platform-specific normalization; validate through the
  platform API/UI when exact acceptance matters.
- Do not turn “best practice” asset counts or durations into compliance failures.
