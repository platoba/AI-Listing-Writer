"""Listing Forensics — detect why a listing underperforms, root cause analysis, fix recommendations."""

from __future__ import annotations

import re
import sqlite3
import json
import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    TITLE = "title"
    DESCRIPTION = "description"
    IMAGES = "images"
    PRICING = "pricing"
    KEYWORDS = "keywords"
    REVIEWS = "reviews"
    COMPETITION = "competition"
    CONVERSION = "conversion"
    COMPLIANCE = "compliance"
    VISIBILITY = "visibility"


# Impact multipliers for scoring
SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 10.0,
    Severity.HIGH: 7.0,
    Severity.MEDIUM: 4.0,
    Severity.LOW: 2.0,
    Severity.INFO: 0.5,
}

# Platform-specific title length requirements
TITLE_LIMITS: dict[str, dict[str, int]] = {
    "amazon": {"min": 50, "max": 200, "ideal_min": 80, "ideal_max": 150},
    "shopee": {"min": 20, "max": 120, "ideal_min": 40, "ideal_max": 100},
    "lazada": {"min": 20, "max": 255, "ideal_min": 50, "ideal_max": 150},
    "aliexpress": {"min": 20, "max": 128, "ideal_min": 40, "ideal_max": 100},
    "ebay": {"min": 20, "max": 80, "ideal_min": 40, "ideal_max": 70},
    "etsy": {"min": 10, "max": 140, "ideal_min": 40, "ideal_max": 100},
    "walmart": {"min": 50, "max": 200, "ideal_min": 80, "ideal_max": 150},
    "tiktok_shop": {"min": 10, "max": 100, "ideal_min": 25, "ideal_max": 80},
}

# Spam/keyword-stuffing patterns
SPAM_PATTERNS = [
    r'(\b\w+\b)\s+\1\s+\1',       # same word 3+ times in a row
    r'[,/|]{3,}',                   # excessive separators
    r'[\!\?]{3,}',                  # excessive punctuation
    r'(?:free|cheap|best)\s+(?:free|cheap|best)',  # stacked superlatives
    r'[A-Z]{20,}',                 # all-caps blocks
]

# Price psychology patterns
PRICING_PATTERNS = {
    "charm": re.compile(r'\d+[.][9][9]$'),          # $X.99
    "round": re.compile(r'\d+[.]00$'),               # $X.00
    "prestige": re.compile(r'\d+[.]0[05]$'),         # $X.00 or $X.05
    "odd": re.compile(r'\d+[.][1-8]\d$'),            # odd cents
}

# Prohibited words in e-commerce (varies by platform)
PROHIBITED_WORDS = [
    "cure", "miracle", "guaranteed results", "weight loss",
    "#1", "number one", "best seller", "top rated",  # unverified claims
    "free", "discount",  # context-dependent
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ForensicIssue:
    category: IssueCategory
    severity: Severity
    title: str
    description: str
    fix: str
    impact_score: float = 0.0
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "fix": self.fix,
            "impact_score": round(self.impact_score, 2),
            "evidence": self.evidence,
        }


@dataclass
class ListingData:
    title: str = ""
    description: str = ""
    bullet_points: list[str] = field(default_factory=list)
    images: int = 0
    price: float = 0.0
    original_price: float = 0.0
    reviews: int = 0
    rating: float = 0.0
    category: str = ""
    platform: str = "amazon"
    keywords: list[str] = field(default_factory=list)
    competitor_price_low: float = 0.0
    competitor_price_high: float = 0.0
    daily_views: int = 0
    daily_orders: int = 0


@dataclass
class ForensicReport:
    listing_id: str
    health_score: float  # 0-100
    grade: str
    issues: list[ForensicIssue]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    top_priorities: list[ForensicIssue]
    estimated_uplift_pct: float  # estimated conversion improvement if fixes applied

    def to_dict(self) -> dict:
        return {
            "listing_id": self.listing_id,
            "health_score": round(self.health_score, 1),
            "grade": self.grade,
            "issues": [i.to_dict() for i in self.issues],
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "top_priorities": [i.to_dict() for i in self.top_priorities],
            "estimated_uplift_pct": round(self.estimated_uplift_pct, 1),
        }


# ---------------------------------------------------------------------------
# Diagnostic Checks
# ---------------------------------------------------------------------------

class TitleDiagnostic:
    """Check title for issues."""

    def check(self, data: ListingData) -> list[ForensicIssue]:
        issues = []
        title = data.title
        platform = data.platform.lower()
        limits = TITLE_LIMITS.get(platform, TITLE_LIMITS["amazon"])

        # Length checks
        if len(title) < limits["min"]:
            issues.append(ForensicIssue(
                category=IssueCategory.TITLE,
                severity=Severity.CRITICAL,
                title="Title too short",
                description=f"Title is {len(title)} chars, minimum is {limits['min']}",
                fix=f"Expand title to at least {limits['ideal_min']} characters with key product attributes",
                evidence=title[:80],
            ))
        elif len(title) > limits["max"]:
            issues.append(ForensicIssue(
                category=IssueCategory.TITLE,
                severity=Severity.HIGH,
                title="Title exceeds maximum length",
                description=f"Title is {len(title)} chars, maximum is {limits['max']}",
                fix=f"Trim title to under {limits['max']} characters — platform may truncate",
                evidence=title[:80],
            ))
        elif len(title) < limits["ideal_min"]:
            issues.append(ForensicIssue(
                category=IssueCategory.TITLE,
                severity=Severity.MEDIUM,
                title="Title could be longer",
                description=f"Title is {len(title)} chars, ideal is {limits['ideal_min']}-{limits['ideal_max']}",
                fix="Add more relevant keywords and product attributes",
            ))

        # Keyword stuffing
        words = title.lower().split()
        word_freq: dict[str, int] = {}
        for w in words:
            w_clean = re.sub(r'[^\w]', '', w)
            if len(w_clean) > 2:
                word_freq[w_clean] = word_freq.get(w_clean, 0) + 1
        repeated = {w: c for w, c in word_freq.items() if c >= 3}
        if repeated:
            issues.append(ForensicIssue(
                category=IssueCategory.TITLE,
                severity=Severity.HIGH,
                title="Keyword stuffing detected",
                description=f"Repeated words: {repeated}",
                fix="Remove repeated keywords — search engines penalize keyword stuffing",
                evidence=str(repeated),
            ))

        # All caps
        if title.isupper() and len(title) > 10:
            issues.append(ForensicIssue(
                category=IssueCategory.TITLE,
                severity=Severity.MEDIUM,
                title="Title is ALL CAPS",
                description="All-caps titles look spammy and may violate platform guidelines",
                fix="Use Title Case or Sentence case",
            ))

        # Missing brand/model
        if data.keywords:
            primary = data.keywords[0].lower()
            if primary not in title.lower():
                issues.append(ForensicIssue(
                    category=IssueCategory.TITLE,
                    severity=Severity.MEDIUM,
                    title="Primary keyword missing from title",
                    description=f"Primary keyword '{data.keywords[0]}' not found in title",
                    fix="Include your primary keyword near the beginning of the title",
                ))

        return issues


class DescriptionDiagnostic:
    """Check description/bullet points."""

    def check(self, data: ListingData) -> list[ForensicIssue]:
        issues = []
        desc = data.description
        bullets = data.bullet_points

        # Empty description
        if not desc.strip() and not bullets:
            issues.append(ForensicIssue(
                category=IssueCategory.DESCRIPTION,
                severity=Severity.CRITICAL,
                title="No description or bullet points",
                description="Listing has no product description",
                fix="Add comprehensive product description with features and benefits",
            ))
            return issues

        # Short description
        total_text = desc + " ".join(bullets)
        word_count = len(total_text.split())
        if word_count < 50:
            issues.append(ForensicIssue(
                category=IssueCategory.DESCRIPTION,
                severity=Severity.HIGH,
                title="Description too thin",
                description=f"Only {word_count} words — aim for 150-300+",
                fix="Expand with features, benefits, use cases, and specifications",
            ))

        # Missing bullets (Amazon/Shopee)
        if not bullets and data.platform.lower() in ("amazon", "shopee", "walmart"):
            issues.append(ForensicIssue(
                category=IssueCategory.DESCRIPTION,
                severity=Severity.HIGH,
                title="No bullet points",
                description="Bullet points are critical for Amazon/Shopee — most shoppers scan bullets first",
                fix="Add 5 bullet points highlighting key benefits",
            ))
        elif bullets and len(bullets) < 3:
            issues.append(ForensicIssue(
                category=IssueCategory.DESCRIPTION,
                severity=Severity.MEDIUM,
                title="Too few bullet points",
                description=f"Only {len(bullets)} bullet points — best practice is 5",
                fix="Add more bullet points covering features, benefits, and specs",
            ))

        # Spam patterns
        for pattern in SPAM_PATTERNS:
            if re.search(pattern, total_text, re.IGNORECASE):
                issues.append(ForensicIssue(
                    category=IssueCategory.DESCRIPTION,
                    severity=Severity.HIGH,
                    title="Spam pattern detected in description",
                    description="Description contains repetitive or spammy content",
                    fix="Clean up the copy — remove excessive repetition and punctuation",
                    evidence=pattern,
                ))
                break

        # No benefits (check for benefit words)
        benefit_words = ["you", "your", "enjoy", "experience", "save", "perfect for"]
        has_benefits = any(bw in total_text.lower() for bw in benefit_words)
        if not has_benefits and word_count > 30:
            issues.append(ForensicIssue(
                category=IssueCategory.DESCRIPTION,
                severity=Severity.MEDIUM,
                title="Description is feature-heavy, benefit-light",
                description="No customer-focused language detected",
                fix="Rewrite features as benefits: 'Made of steel' → 'Built to last for years'",
            ))

        return issues


class ImageDiagnostic:
    """Check image issues."""

    def check(self, data: ListingData) -> list[ForensicIssue]:
        issues = []
        img_count = data.images
        platform = data.platform.lower()

        min_images = {"amazon": 5, "shopee": 3, "ebay": 3, "etsy": 3}.get(platform, 3)
        ideal_images = {"amazon": 7, "shopee": 6, "ebay": 6, "etsy": 5}.get(platform, 5)

        if img_count == 0:
            issues.append(ForensicIssue(
                category=IssueCategory.IMAGES,
                severity=Severity.CRITICAL,
                title="No images",
                description="Listing has zero images — this is a conversion killer",
                fix=f"Upload at least {min_images} high-quality product images",
            ))
        elif img_count < min_images:
            issues.append(ForensicIssue(
                category=IssueCategory.IMAGES,
                severity=Severity.HIGH,
                title="Too few images",
                description=f"Only {img_count} images, recommended minimum is {min_images}",
                fix=f"Add more images: lifestyle, detail, scale, packaging, infographic (target {ideal_images})",
            ))
        elif img_count < ideal_images:
            issues.append(ForensicIssue(
                category=IssueCategory.IMAGES,
                severity=Severity.LOW,
                title="Image count below ideal",
                description=f"{img_count} images — adding more can increase conversion by 5-10%",
                fix=f"Target {ideal_images} images including infographics and lifestyle shots",
            ))

        return issues


class PricingDiagnostic:
    """Check pricing issues."""

    def check(self, data: ListingData) -> list[ForensicIssue]:
        issues = []
        price = data.price

        if price <= 0:
            issues.append(ForensicIssue(
                category=IssueCategory.PRICING,
                severity=Severity.CRITICAL,
                title="No price set",
                description="Product has no price",
                fix="Set a competitive price based on market research",
            ))
            return issues

        # Price vs competition
        if data.competitor_price_low > 0 and price < data.competitor_price_low * 0.5:
            issues.append(ForensicIssue(
                category=IssueCategory.PRICING,
                severity=Severity.HIGH,
                title="Price suspiciously low",
                description=f"${price:.2f} is less than 50% of lowest competitor (${data.competitor_price_low:.2f})",
                fix="Very low prices signal low quality — consider raising to at least 70% of market average",
            ))
        elif data.competitor_price_high > 0 and price > data.competitor_price_high * 1.3:
            issues.append(ForensicIssue(
                category=IssueCategory.PRICING,
                severity=Severity.MEDIUM,
                title="Price above market range",
                description=f"${price:.2f} is 30%+ above highest competitor (${data.competitor_price_high:.2f})",
                fix="Justify premium pricing with superior images, A+ content, and brand story",
            ))

        # Charm pricing
        price_str = f"{price:.2f}"
        if not PRICING_PATTERNS["charm"].search(price_str):
            issues.append(ForensicIssue(
                category=IssueCategory.PRICING,
                severity=Severity.LOW,
                title="Not using charm pricing",
                description=f"Price ${price_str} doesn't use .99 ending",
                fix="Charm pricing ($X.99) typically converts 8-10% better than round numbers",
            ))

        # Discount display
        if data.original_price > 0 and data.original_price > price:
            discount_pct = (data.original_price - price) / data.original_price * 100
            if discount_pct > 70:
                issues.append(ForensicIssue(
                    category=IssueCategory.PRICING,
                    severity=Severity.MEDIUM,
                    title="Excessive discount displayed",
                    description=f"{discount_pct:.0f}% discount — may look fraudulent",
                    fix="Keep displayed discounts under 50% for credibility",
                ))

        return issues


class KeywordDiagnostic:
    """Check keyword optimization."""

    def check(self, data: ListingData) -> list[ForensicIssue]:
        issues = []
        all_text = (data.title + " " + data.description + " " + " ".join(data.bullet_points)).lower()

        if not data.keywords:
            issues.append(ForensicIssue(
                category=IssueCategory.KEYWORDS,
                severity=Severity.HIGH,
                title="No target keywords defined",
                description="Cannot assess keyword optimization without target keywords",
                fix="Research and define 5-10 target keywords for this listing",
            ))
            return issues

        missing = [kw for kw in data.keywords if kw.lower() not in all_text]
        if missing:
            severity = Severity.HIGH if len(missing) > len(data.keywords) // 2 else Severity.MEDIUM
            issues.append(ForensicIssue(
                category=IssueCategory.KEYWORDS,
                severity=severity,
                title=f"{len(missing)} target keywords missing from listing",
                description=f"Missing: {', '.join(missing[:5])}",
                fix="Incorporate missing keywords naturally into title, bullets, and description",
                evidence=", ".join(missing),
            ))

        # Keyword in title check
        title_lower = data.title.lower()
        keywords_in_title = [kw for kw in data.keywords if kw.lower() in title_lower]
        if not keywords_in_title:
            issues.append(ForensicIssue(
                category=IssueCategory.KEYWORDS,
                severity=Severity.HIGH,
                title="No target keywords in title",
                description="Title doesn't contain any of your target keywords",
                fix="Place your primary keyword near the beginning of the title",
            ))

        return issues


class ReviewDiagnostic:
    """Check review/rating issues."""

    def check(self, data: ListingData) -> list[ForensicIssue]:
        issues = []

        if data.reviews == 0:
            issues.append(ForensicIssue(
                category=IssueCategory.REVIEWS,
                severity=Severity.HIGH,
                title="Zero reviews",
                description="Products with no reviews convert 270% worse than those with 5+ reviews",
                fix="Launch a review generation strategy: Vine, follow-up emails, inserts",
            ))
        elif data.reviews < 10:
            issues.append(ForensicIssue(
                category=IssueCategory.REVIEWS,
                severity=Severity.MEDIUM,
                title="Very few reviews",
                description=f"Only {data.reviews} reviews — social proof is weak",
                fix="Accelerate review generation: aim for 15+ reviews in the first 30 days",
            ))

        if data.rating > 0 and data.rating < 3.5:
            issues.append(ForensicIssue(
                category=IssueCategory.REVIEWS,
                severity=Severity.CRITICAL,
                title="Low rating",
                description=f"Rating is {data.rating:.1f}/5.0 — below the suppression threshold",
                fix="Address common complaints: product quality, shipping, packaging",
            ))
        elif data.rating > 0 and data.rating < 4.0:
            issues.append(ForensicIssue(
                category=IssueCategory.REVIEWS,
                severity=Severity.HIGH,
                title="Rating below average",
                description=f"Rating is {data.rating:.1f}/5.0 — most top sellers have 4.3+",
                fix="Analyze negative reviews for recurring issues and fix root causes",
            ))

        return issues


class ConversionDiagnostic:
    """Check conversion rate issues."""

    def check(self, data: ListingData) -> list[ForensicIssue]:
        issues = []

        if data.daily_views > 0 and data.daily_orders >= 0:
            conv_rate = (data.daily_orders / data.daily_views * 100) if data.daily_views > 0 else 0

            if conv_rate < 1.0 and data.daily_views > 10:
                issues.append(ForensicIssue(
                    category=IssueCategory.CONVERSION,
                    severity=Severity.CRITICAL,
                    title="Very low conversion rate",
                    description=f"Conversion rate: {conv_rate:.2f}% ({data.daily_orders}/{data.daily_views} daily)",
                    fix="Overhaul listing: images first, then title, bullets, and pricing",
                ))
            elif conv_rate < 5.0 and data.daily_views > 10:
                issues.append(ForensicIssue(
                    category=IssueCategory.CONVERSION,
                    severity=Severity.MEDIUM,
                    title="Below-average conversion rate",
                    description=f"Conversion rate: {conv_rate:.2f}% — average is 5-15% on Amazon",
                    fix="A/B test main image, adjust price, and improve bullet points",
                ))

        if data.daily_views == 0:
            issues.append(ForensicIssue(
                category=IssueCategory.VISIBILITY,
                severity=Severity.CRITICAL,
                title="Zero traffic",
                description="Listing is getting no views — visibility problem",
                fix="Check: (1) keywords indexed? (2) PPC running? (3) BSR in category?",
            ))
        elif data.daily_views < 10:
            issues.append(ForensicIssue(
                category=IssueCategory.VISIBILITY,
                severity=Severity.HIGH,
                title="Very low traffic",
                description=f"Only {data.daily_views} daily views — need more visibility",
                fix="Increase PPC budget, optimize backend keywords, run promotions",
            ))

        return issues


# ---------------------------------------------------------------------------
# Forensic Store (SQLite)
# ---------------------------------------------------------------------------

class ForensicStore:
    """Persist forensic reports for trend tracking."""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS forensic_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                health_score REAL NOT NULL,
                grade TEXT NOT NULL,
                critical_count INTEGER DEFAULT 0,
                high_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                low_count INTEGER DEFAULT 0,
                issues_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_forensic_listing ON forensic_reports(listing_id);
            CREATE INDEX IF NOT EXISTS idx_forensic_created ON forensic_reports(created_at);
        """)
        self._conn.commit()

    def save(self, report: ForensicReport) -> int:
        cur = self._conn.execute("""
            INSERT INTO forensic_reports
            (listing_id, health_score, grade, critical_count, high_count, medium_count, low_count, issues_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.listing_id, report.health_score, report.grade,
            report.critical_count, report.high_count, report.medium_count, report.low_count,
            json.dumps([i.to_dict() for i in report.issues]),
        ))
        self._conn.commit()
        return cur.lastrowid  # type: ignore

    def history(self, listing_id: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute("""
            SELECT * FROM forensic_reports WHERE listing_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (listing_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def worst_listings(self, limit: int = 10) -> list[dict]:
        rows = self._conn.execute("""
            SELECT listing_id, MIN(health_score) as worst_score,
                   SUM(critical_count) as total_critical
            FROM forensic_reports
            GROUP BY listing_id
            ORDER BY worst_score ASC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def trend(self, listing_id: str) -> list[dict]:
        rows = self._conn.execute("""
            SELECT health_score, grade, critical_count, created_at
            FROM forensic_reports WHERE listing_id = ?
            ORDER BY created_at ASC
        """, (listing_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Listing Forensics Engine (Main Class)
# ---------------------------------------------------------------------------

def _grade(score: float) -> str:
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B+"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


class ListingForensics:
    """Main entry point: run full diagnostic on a listing."""

    def __init__(self, db_path: str = ":memory:"):
        self.diagnostics = [
            TitleDiagnostic(),
            DescriptionDiagnostic(),
            ImageDiagnostic(),
            PricingDiagnostic(),
            KeywordDiagnostic(),
            ReviewDiagnostic(),
            ConversionDiagnostic(),
        ]
        self.store = ForensicStore(db_path)

    def diagnose(self, data: ListingData, listing_id: str = "") -> ForensicReport:
        all_issues: list[ForensicIssue] = []

        for diag in self.diagnostics:
            issues = diag.check(data)
            all_issues.extend(issues)

        # Calculate impact scores
        for issue in all_issues:
            issue.impact_score = SEVERITY_WEIGHTS.get(issue.severity, 1.0)

        # Sort by severity
        all_issues.sort(key=lambda i: i.impact_score, reverse=True)

        # Count by severity
        critical = sum(1 for i in all_issues if i.severity == Severity.CRITICAL)
        high = sum(1 for i in all_issues if i.severity == Severity.HIGH)
        medium = sum(1 for i in all_issues if i.severity == Severity.MEDIUM)
        low = sum(1 for i in all_issues if i.severity == Severity.LOW)

        # Health score (start at 100, deduct)
        deduction = sum(i.impact_score for i in all_issues)
        health_score = max(0, min(100, 100 - deduction))
        grade = _grade(health_score)

        # Top priorities (top 5 highest-impact)
        top_priorities = all_issues[:5]

        # Estimated uplift: each critical fix ~ 10%, high ~ 5%, medium ~ 2%
        uplift = critical * 10 + high * 5 + medium * 2
        uplift = min(uplift, 80)  # cap at 80%

        report = ForensicReport(
            listing_id=listing_id or "unknown",
            health_score=health_score,
            grade=grade,
            issues=all_issues,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            top_priorities=top_priorities,
            estimated_uplift_pct=uplift,
        )

        if listing_id:
            self.store.save(report)

        return report

    def batch_diagnose(self, listings: list[tuple[str, ListingData]]) -> list[ForensicReport]:
        """Diagnose multiple listings."""
        return [self.diagnose(data, lid) for lid, data in listings]

    def compare(self, reports: list[ForensicReport]) -> dict:
        """Compare multiple forensic reports."""
        if not reports:
            return {}
        return {
            "best": max(reports, key=lambda r: r.health_score).listing_id,
            "worst": min(reports, key=lambda r: r.health_score).listing_id,
            "avg_score": round(sum(r.health_score for r in reports) / len(reports), 1),
            "total_critical_issues": sum(r.critical_count for r in reports),
            "common_categories": self._common_issues(reports),
        }

    def _common_issues(self, reports: list[ForensicReport]) -> dict[str, int]:
        cat_counts: dict[str, int] = {}
        for r in reports:
            for issue in r.issues:
                cat = issue.category.value
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        return dict(sorted(cat_counts.items(), key=lambda x: x[1], reverse=True))

    def report_text(self, report: ForensicReport) -> str:
        lines = [
            "=" * 55,
            "LISTING FORENSICS REPORT",
            "=" * 55,
            f"Listing: {report.listing_id}",
            f"Health Score: {report.health_score:.1f}/100 ({report.grade})",
            f"Issues: {report.critical_count} critical, {report.high_count} high, "
            f"{report.medium_count} medium, {report.low_count} low",
            f"Estimated Uplift: +{report.estimated_uplift_pct:.0f}% if all fixes applied",
            "",
        ]

        if report.top_priorities:
            lines.append("🔥 TOP PRIORITIES:")
            for i, issue in enumerate(report.top_priorities, 1):
                severity_icon = {
                    "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"
                }.get(issue.severity.value, "")
                lines.append(f"  {i}. {severity_icon} [{issue.category.value.upper()}] {issue.title}")
                lines.append(f"     {issue.description}")
                lines.append(f"     Fix: {issue.fix}")
                lines.append("")

        if len(report.issues) > 5:
            lines.append(f"... and {len(report.issues) - 5} more issues")

        lines.append("=" * 55)
        return "\n".join(lines)
