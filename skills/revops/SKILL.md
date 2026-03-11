---
name: revops
description: >
  Lead scoring, lifecycle stages, CRM automation, and marketing-to-sales
  handoff for campaigns generating leads via Meta ads. Covers HubSpot,
  Salesforce, and general CRM logic. Triggers on: "revenue operations",
  "revops", "lead scoring", "CRM", "lifecycle stages", "marketing to sales
  handoff", "MQL", "SQL", "lead qualification", "CRM automation".
argument-hint: "<CRM platform> | <lead gen campaign name>"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
---

# RevOps — Lead Scoring, Lifecycle & CRM Automation

Designs the marketing-to-sales infrastructure for Meta lead gen campaigns:
lead scoring model, lifecycle stage definitions, CRM automation rules, and
handoff criteria between marketing and sales.

## Process

1. Identify CRM platform and sales process context
2. Read campaign brief if available (`campaigns/{name}/brief.md`)
3. Define lead scoring model
4. Define lifecycle stages and stage-change triggers
5. Design CRM automation sequences
6. Define marketing-to-sales handoff criteria (MQL → SQL)
7. Document in output

---

## Lead Scoring Model

Score leads on two dimensions: **Fit** (who they are) and **Engagement**
(what they've done). Combine for a total score.

### Fit Score (Demographic / Firmographic)
Points assigned based on how closely the lead matches the ideal customer profile:

| Attribute | Points | Rationale |
|-----------|--------|-----------|
| Job title matches ICP | +20 | Direct buyer or influencer |
| Company size in target range | +15 | Budget likelihood |
| Industry matches ICP | +15 | Relevance fit |
| Geography in target market | +10 | Sales territory fit |
| Qualifying question answered correctly | +15 | Explicit intent signal |
| Personal email (not work) | −10 | Lower conversion likelihood |
| Company size too small for offer | −15 | Poor fit |

### Engagement Score (Behavioral)
Points assigned based on actions taken:

| Action | Points | Decay |
|--------|--------|-------|
| Submitted lead form from Meta ad | +25 | None |
| Visited pricing page | +20 | −5/week after 2 weeks |
| Visited product/features page | +15 | −3/week after 2 weeks |
| Opened marketing email | +5 | −1/week after 1 week |
| Clicked link in email | +10 | −2/week after 1 week |
| Watched demo video (>50%) | +20 | None |
| Returned to website 2+ times | +15 | None |
| Unsubscribed from email | −30 | Permanent |

### Lead Score Thresholds
| Total Score | Stage | Action |
|-------------|-------|--------|
| 0–29 | Lead | Enter nurture sequence |
| 30–59 | Marketing Qualified Lead (MQL) | Increase nurture intensity |
| 60–79 | Sales Qualified Lead (SQL) | Notify sales within 24 hours |
| 80+ | Sales Accepted Lead (SAL) | Sales outreach within 2 hours |

---

## Lifecycle Stage Definitions

| Stage | Definition | Entry Trigger | Exit Trigger |
|-------|-----------|--------------|-------------|
| Lead | Contact in database | Form submission | Score ≥30 |
| MQL | Meets basic fit + engagement criteria | Score ≥30 | Score ≥60 or disqualified |
| SQL | Sales-ready, meets ICP criteria | Score ≥60 | Sales accepted or disqualified |
| Opportunity | Active sales conversation | Sales creates deal | Won or lost |
| Customer | Purchased | Deal marked Won | — |
| Disqualified | Does not meet criteria | Sales rejects or score drops | Lead again if re-engages |

---

## CRM Automation Rules

### On Lead Creation (Meta ad form submission)
1. Create contact in CRM with source `meta_paid`
2. Assign to marketing owner
3. Tag with campaign name and ad set
4. Enroll in lead nurture email sequence (see below)
5. Send confirmation email immediately

### Lead Nurture Email Sequence
Design a 5-email sequence for new leads:

| Email | Timing | Subject | Goal |
|-------|--------|---------|------|
| 1 | Immediately | "{Lead magnet} is here" | Deliver value, set expectation |
| 2 | Day 2 | "One thing [ICP] always gets wrong" | Educate, build authority |
| 3 | Day 4 | "How [Client] got [result]" | Social proof, case study |
| 4 | Day 7 | "[Product] in 2 minutes" | Product awareness |
| 5 | Day 10 | "Quick question for you" | Reply or book CTA |

### On MQL Threshold Reached (Score ≥30)
1. Add "MQL" tag to contact
2. Increase email frequency (shorten sequence intervals)
3. Add to high-intent retargeting audience in Meta

### On SQL Threshold Reached (Score ≥60)
1. Create task for sales rep: "Follow up within 24 hours"
2. Send internal Slack/email notification to sales team
3. Move contact to sales pipeline
4. Add to "hot prospect" Meta retargeting segment
5. Pause generic nurture sequence; switch to sales-specific sequence

---

## Marketing-to-Sales Handoff Criteria

Define the exact criteria a lead must meet for sales to accept:

**MQL → SQL Handoff Checklist:**
- [ ] Lead score ≥60
- [ ] Work email provided (not personal)
- [ ] Company size matches ICP (specify range)
- [ ] Job title is buyer, influencer, or economic buyer
- [ ] No disqualifying responses in lead form
- [ ] Lead submitted within last 30 days (recency filter)

**Sales Response SLA:**
- SQL: respond within 24 business hours
- SAL (score ≥80): respond within 2 business hours
- Speed-to-lead is a key conversion driver — every hour of delay reduces
  conversion rate by ~10%

---

## Attribution Setup

Connect Meta campaign data to CRM for closed-loop reporting:
- Store `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` on contact
  record at first touch
- Track original ad creative (`utm_content`) through to Opportunity stage
- Report: Leads by campaign → MQL by campaign → SQL by campaign → Revenue by campaign

---

## Output

Deliver a RevOps specification document covering:
- Lead scoring model (fit + engagement)
- Lifecycle stage definitions with triggers
- CRM automation rules (5 workflows minimum)
- Email nurture sequence outline (5 emails)
- MQL → SQL handoff criteria

If a campaign is active, save to `campaigns/{name}/revops.md`.
