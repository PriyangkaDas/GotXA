# GotXA SaaS - Pricing Calculator & ROI Estimator

> **SaaS Documentation Suite**:
> - 🚀 **Commercial Strategy**: [`GotXA_SaaS_Strategy.md`](GotXA_SaaS_Strategy.md)
> - 🛠️ **Technical Architecture**: [`GotXA_SaaS_Technical_Implementation.md`](GotXA_SaaS_Technical_Implementation.md)
> - 📑 **Directory Index**: [`README.md`](README.md)

## QUICK PRICING CALCULATOR

Use this to quote customers based on their needs:

```
┌─────────────────────────────────────────────────────────┐
│ CUSTOMER CONFIGURATION                                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Company: ________________                              │
│ Industry: ________________                             │
│ Employees: ________                                    │
│                                                         │
│ INPUTS:                                                 │
│ ├─ Users needing access: ________                      │
│ ├─ Estimated daily logs (GB): ________                │
│ ├─ Retention requirement (months): ________           │
│ ├─ Playbooks needed: ________                         │
│ ├─ Support level: [Standard / Premium / 24/7]         │
│ └─ Features: [Basic / SOAR / TI / All]                │
│                                                         │
└─────────────────────────────────────────────────────────┘

CALCULATION:

Step 1: Determine Base Tier
├─ <50 employees → Starter ($500/mo)
├─ 50-500 employees → Professional ($3,000/mo)
└─ 500+ employees → Enterprise (Custom)

Step 2: Add Usage Overages
├─ Daily logs: 10 GB = ~300 GB/month
├─ Starter limit: 100 GB → Overage = 200 GB
├─ Overage charge: 200 GB × $0.50 = $100/mo
└─ Subtotal: $500 + $100 = $600/mo

Step 3: Add Retention Premium
├─ Standard (90 days): Included
├─ Extended (1 year): $500-1,000/mo
└─ Premium (3+ years): $2,000-5,000/mo

Step 4: Add Features
├─ Advanced TI feeds: $2,000/mo
├─ SOAR automation (unlimited): $1,500/mo
├─ Premium support: $5,000/mo
└─ Custom integration: $10K-30K (one-time)

TOTAL ANNUAL CONTRACT VALUE (ACV):
$600 × 12 = $7,200/year
└─ Pro-rated first month (if mid-month start)

PROPOSAL:
├─ Monthly: $600
├─ Annual: $7,000 (16% discount)
└─ Setup fee: $2,000 (one-time onboarding)
```

---

## ROI CALCULATOR FOR CUSTOMERS

**Frame: "How much will GotXA save you vs. Splunk?"**

```
Current State (Splunk):
├─ Splunk licenses (200GB/day): $400,000/year
├─ Splunk support: $50,000/year
├─ Internal team managing Splunk: 2 FTE @ $200K = $400,000/year
├─ Infrastructure (servers, storage): $100,000/year
└─ TOTAL: $950,000/year

GotXA SaaS (Equivalent):
├─ GotXA platform: $50,000/year (usage-based)
├─ GotXA support: $0 (included)
├─ Internal team (1 FTE instead of 2): $200,000/year
├─ Infrastructure: $0 (managed by GotXA)
└─ TOTAL: $250,000/year

SAVINGS:
├─ Year 1: $700,000 (26% ROI in first 3 months)
├─ Year 2: $700,000
├─ Year 3: $700,000
└─ 3-year savings: $2,100,000

PAYBACK PERIOD: Immediate (first month)
├─ Implement cost: $25,000 (onboarding)
├─ Monthly savings: $59,000
├─ Payback: <1 week
```

---

## COMPETITIVE WIN PRICING

**Undercut competitor by 30-40% for new customers:**

```
Splunk                  →  GotXA equivalent
$10,000/month           →  $6,000/month (40% savings)
$50,000/month           →  $25,000/month
$100,000/month          →  $60,000/month

BUT: Include features Splunk charges extra for:
├─ SOAR (Splunk: $15K extra) → GotXA: Included
├─ TI feeds (Splunk: $10K extra) → GotXA: Included
├─ Premium support (Splunk: $20K extra) → GotXA: Included
├─ Custom dashboard → GotXA: Included
└─ Effective savings: 50%+ when accounting for add-ons
```

---

## MULTI-YEAR COMMITMENT DISCOUNTS

**Incentivize longer commitments (improves cash flow & retention):**

```
1-Year Contract: List price
├─ Monthly: $600
└─ Annual: $7,000 (17% savings)

2-Year Contract: 20% discount
├─ Annual: $5,600
└─ Total: $11,200

3-Year Contract: 30% discount
├─ Annual: $4,900
└─ Total: $14,700

5-Year Contract: 40% discount (Enterprise only)
├─ Annual: $4,200
└─ Total: $21,000

Example ROI for customer signing 3-year:
├─ GotXA 3-year cost: $14,700
├─ Splunk 3-year cost: $2,850,000
├─ Savings: $2,835,300
└─ Payback: Immediate
```

---

## EXPANSION REVENUE MODEL

**Don't just get one tier; upsell expansions:**

```
Customer Lifecycle:

Month 1-3: Starter ($500/mo)
├─ Proves value
├─ Small security team pilots
└─ Engagement metrics tracked

Month 4-6: Upsell to Professional ($3,000/mo)
├─ "Your log volume now 200GB/mo (Starter max: 100GB)"
├─ "Advanced threat hunting dashboard available"
├─ "SOAR automation will save your team 10 hours/week"
└─ Pitch: +$2,500/mo for $50K value

Month 7-12: Add-on Services
├─ Advanced TI feeds: +$2,000/mo
├─ Managed incident response: +$10K/incident
├─ Custom playbook development: +$15K
└─ Total ACV grows: $3,500 → $8,500 → $15,500

Year 2: Enterprise Upsell
├─ "Ready for enterprise deployment?"
├─ Offer self-hosted option or dedicated infrastructure
├─ Price: $30K-100K/year
└─ Or migrate to managed Enterprise tier
```

**Revenue Per Account Over 3 Years:**

```
Starter → Professional → Enterprise
Month 1:    $500
Month 6:    $3,500 (+ $2,000 TI)
Month 12:   $5,500
Month 24:   $10,000 (Enterprise upsell)
Month 36:   $25,000 (Managed IR + custom dev)

Cumulative Customer Lifetime Value:
Year 1:   $6,000 + $21,000 = $27,000
Year 2:   $35,000 + $5,000 (new features) = $40,000
Year 3:   $120,000 (enterprise)
TOTAL:    $187,000 LTV

Compare to CAC: $8,000
LTV:CAC = 23x (exceptional)
```

---

## SALES CONVERSATION TEMPLATE

**When prospecting:**

```
Opening: Pain Point
"I noticed your org is using [competitor]. 
How's your current SIEM working for you?"

Listen for: Alert fatigue, slow MTTR, cost, limited SOAR

Pivot to GotXA:
"We've helped companies like [similar company] cut their 
security tooling costs by 60% while actually improving 
MTTR by 40%. Interested in seeing how?"

Discovery:
"Tell me about your:
├─ Current log volume?
├─ Number of security analysts?
├─ Biggest pain points?
├─ Budget in security tools?"

Qualification:
"If I could show you a solution that:
├─ Costs $X/month (vs. your current $Y)
├─ Includes SOAR automation (vs. Splunk's separate $Z)
├─ Has you live in 2 weeks
Would that be interesting?"

Demo:
"Let me show you how we'd ingest YOUR log types..."
(Use their real data/logs if possible)

Trial Offer:
"Take 30 days free. Ingest your actual logs. 
If you don't see the value, walk away."
(90% of people who trial convert)

Pricing Anchor:
"We typically charge $3K/mo for your profile.
But for annual commitment, I can do $2,500/mo."

Close:
"Which works better—starting with trial next week 
or getting a formal proposal first?"
```

---

## ANNUAL CONTRACT VALUE (ACV) TARGETS

```
YEAR 1: TARGET 50 CUSTOMERS

10 @ Starter tier:      $500 × 12 × 10 = $60,000
20 @ Professional tier: $3,500 × 12 × 20 = $840,000
15 @ Enterprise tier:   $12,000 × 12 × 15 = $2,160,000
5 @ MSSP tier:          $8,000 × 12 × 5 = $480,000

Subtotal: $3,540,000

Less: Churn (assume 10% lost):
─ 5 customers × average $4,000 = -$240,000

NET: $3,300,000 ARR by end of Year 1
(Conservative estimate: $2.5M accounting for ramp)

---

YEAR 2: TARGET 180 CUSTOMERS

Existing (50 customers):
├─ 40 retained (80% retention): $3,200,000 ARR
└─ 10 expanded (upsell): +$800,000

New (130 customers):
├─ 40 @ Starter: $240,000
├─ 60 @ Professional: $2,520,000
└─ 30 @ Enterprise: $4,320,000

Subtotal: $11,080,000
Less churn: -10% = -$1,108,000
NET: $9,972,000 → $8.5M ARR

---

YEAR 3: TARGET 400 CUSTOMERS

Existing (180): $8,000,000 (with expansion)
New (220): $15,000,000
Churn: -$1,000,000
NET: $22,000,000 ARR
```

---

## DEAL SIZE DISTRIBUTION

```
Starter Deals (<$50K/year):       20% of pipeline
├─ Velocity: High (5-10 day sales cycle)
├─ Close rate: 70%+
├─ Margin: 40%
└─ Usage: For pilot/PoC

Professional Deals ($50-150K/yr): 50% of pipeline
├─ Velocity: Medium (15-30 day sales cycle)
├─ Close rate: 50%+
├─ Margin: 60%
└─ Usage: For SMB/mid-market

Enterprise Deals ($150K+/yr):     30% of pipeline
├─ Velocity: Slow (60-120 day sales cycle)
├─ Close rate: 30-40%
├─ Margin: 70%+
└─ Usage: For Fortune 500

Weighted average:
(20% × $6K) + (50% × $75K) + (30% × $300K) = $106K ACVTarget: 20-30 deals/year to hit $2.5M ARR
```

---

## FINANCIAL WATERFALL (Per Customer)

```
Example: Professional Tier ($3,000/month)

Monthly Revenue:                           $3,000
├─ List Price: $3,500
└─ Annual discount (17%): -$500

COGS (Cost to serve):
├─ Cloud infrastructure: -$900 (30%)
├─ Support (L1/L2): -$300 (10%)
└─ Total COGS: -$1,200

GROSS PROFIT:                              $1,800 (60%)

OpEx (allocated):
├─ Sales/Marketing (CAC amortized): -$200
├─ Engineering (feature development): -$300
├─ G&A (support, legal, billing): -$150
└─ Total OpEx: -$650

CONTRIBUTION MARGIN:                       $1,150 (38%)

Breakeven: 7 months (($8,000 CAC) / $1,150)
LTV: $1,150 × 24 months = $27,600
LTV:CAC: 3.5x (healthy for SaaS)

Note: Improves to 5-8x LTV:CAC with expansion revenue
```

---

## DISCOUNT GUARDRAILS

**NEVER go below these prices:**

```
Absolute Floor Pricing:
├─ Starter minimum: $300/mo (avoid with discount)
├─ Professional minimum: $2,000/mo (core value tier)
├─ Enterprise minimum: $8,000/mo

Volume Discounts:
├─ 1-10 customers: List price
├─ 11-25 customers (same company): 10% off
├─ 26+ customers (same company): 20% off
└─ Multi-year (3yr): 30% off max

Reasons NOT to discount:
├─ Signals low value
├─ Commoditizes your product
├─ Hurts brand positioning
├─ Attracts wrong customer type (price-sensitive, high churn)
└─ Annoys customers who paid full price

Instead of discount, offer:
├─ Extended trial (60 days vs 30)
├─ Premium support
├─ Custom onboarding
├─ Free training
└─ Faster implementation
```

---

## DECISION TREE FOR SALES

```
Customer asks: "What's your cheapest price?"

Answer: "We don't compete on price. 
We compete on value. Splunk costs 10x more.
The question is: are we a fit for your requirements?"

If they push for discount:
├─ Ask: "Is budget the main concern?"
│  └─ Yes → Recommend Starter tier (pilot approach)
│  └─ No → Emphasize ROI + time-to-value
│
├─ Offer: Multi-year discount (15-20%) not single month
│
└─ Pivot: "What if we got you up for free 30 days?
           Would that help justify the investment?"

If they still won't budge:
├─ They're not your customer (price-shopper)
├─ Let them go (high churn risk)
└─ Move to next lead (sales rep time > this deal)

Remember:
"A customer acquired on discount is a customer 
that will churn on discount. You don't want them."
```

