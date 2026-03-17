---
name: ads-landing
description: "Landing page quality assessment for paid advertising campaigns. Evaluates message match, page speed, mobile experience, trust signals, form optimization, and conversion rate potential. Use when user says 'landing page', 'post-click experience', 'landing page audit', 'conversion rate', or 'landing page optimization'."
---

# Landing Page Quality for Ad Campaigns

## Process

1. Collect landing page URLs from active ad campaigns
2. Read `ads/references/benchmarks.md` for conversion rate benchmarks
3. Read `ads/references/conversion-tracking.md` for pixel/tag verification
4. **Validate**: confirm URLs are accessible and rendering before scoring
5. Assess each landing page for ad-specific quality factors
6. Score landing pages and identify improvement opportunities
7. **Validate**: verify tracking pixels fire on thank-you page before finalizing scores
8. Generate recommendations prioritized by conversion impact

## Message Match Assessment

### What to Check
- **Headline match**: landing page H1 reflects ad copy headline/keyword
- **Offer match**: promoted offer visible above fold
- **CTA match**: landing page CTA matches ad's promised action
- **Visual match**: consistent imagery between ad creative and page
- **Keyword match**: search keyword appears naturally in page content

### Message Match Scoring
| Level | Description | Score |
|-------|-------------|-------|
| Exact match | Headline, offer, CTA all align | 100% |
| Partial match | Headline matches but offer/CTA differs | 60% |
| Weak match | Generic page, loosely related | 30% |
| Mismatch | Page doesn't reflect ad promise | 0% |

## Page Speed Assessment

### Thresholds (Ad Landing Pages)
| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| LCP | <2.5s | 2.5-4.0s | >4.0s |
| FID/INP | <100ms | 100-200ms | >200ms |
| CLS | <0.1 | 0.1-0.25 | >0.25 |
| Time to Interactive | <3.0s | 3.0-5.0s | >5.0s |
| Page weight | <2MB | 2-5MB | >5MB |

### Speed Test Commands
```bash
# Lighthouse CLI audit
npx lighthouse <URL> --output=json --only-categories=performance

# PageSpeed Insights API
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=<URL>&strategy=mobile"
```

### Common Speed Issues
- Hero images not compressed (use WebP/AVIF)
- Too many third-party scripts
- Render-blocking CSS/JS above fold
- No lazy loading for below-fold content

## Mobile Experience Checklist

- [ ] Tap targets: ≥48x48px with ≥8px spacing
- [ ] Font size: ≥16px body text
- [ ] Form fields: keyboard type matches input (email, phone, number)
- [ ] CTA button: full-width on mobile, visible without scrolling
- [ ] No horizontal scroll
- [ ] Images responsive and properly sized
- [ ] Phone number clickable (tel: link)
- [ ] No interstitials blocking content on load

## Trust Signals

### Above the Fold
- Company logo, social proof, security badges, client logos, star ratings

### Below the Fold
- Full testimonials with names/photos, case study metrics, certifications, privacy policy link

## Form Optimization

### Form Length Impact on CVR
| Fields | Expected CVR Impact | Use Case |
|--------|-------------------|----------|
| 1-3 | Highest | Top-of-funnel, free offer |
| 4-5 | Moderate | Mid-funnel, qualified leads |
| 6-8 | Lower | Bottom-funnel, sales-ready |
| 9+ | Lowest | Only high-value offers |

### Form Best Practices
- Pre-fill where possible, multi-step for 5+ fields
- Inline validation, specific submit button text ("Get My Free Quote" not "Submit")
- Thank you page with clear next steps

## Ad-Specific Elements

### UTM & Click ID Handling
- UTM parameters captured and passed to form/CRM
- Click IDs preserved: gclid, fbclid, ttclid, msclkid

### Conversion Tracking Verification
```bash
# Verify pixel fires on thank-you page (check network tab for these):
# Google: google-analytics.com/collect or googleads.g.doubleclick.net/pagead/conversion
# Meta: facebook.com/tr
# TikTok: analytics.tiktok.com
# LinkedIn: px.ads.linkedin.com
```

### Platform-Specific Requirements
| Platform | Key Requirement |
|----------|----------------|
| Google | Landing page experience affects QS → ad rank and CPC |
| Meta | Slow pages penalize delivery |
| TikTok | Mobile-first mandatory (95%+ mobile traffic) |
| Microsoft | Desktop optimization matters more (higher desktop %) |

## Output

### Landing Page Assessment

```
Landing Page Health

Message Match:    ████████░░  XX/100
Page Speed:       ██████████  XX/100
Mobile:           ███████░░░  XX/100
Trust Signals:    █████░░░░░  XX/100
Form Quality:     ████████░░  XX/100
```

### Deliverables
- `LANDING-PAGE-REPORT.md` — Per-page assessment with scores
- Message match analysis per ad-to-page combination
- Page speed improvement priorities
- Mobile experience fixes
- Form optimization recommendations
- Quick Wins sorted by conversion impact
