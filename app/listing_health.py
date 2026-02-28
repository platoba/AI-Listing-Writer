"""Listing Health Monitor - automated health scoring, degradation detection, and alerts.

Monitors listing quality across multiple dimensions: SEO, content,
pricing, images, compliance, and tracks changes over time.
"""

import json
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class HealthGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertType(str, Enum):
    SCORE_DROP = "score_drop"
    MISSING_FIELD = "missing_field"
    SEO_ISSUE = "seo_issue"
    CONTENT_QUALITY = "content_quality"
    PRICING_ANOMALY = "pricing_anomaly"
    COMPLIANCE_VIOLATION = "compliance_violation"
    IMAGE_ISSUE = "image_issue"
    STALE_LISTING = "stale_listing"


@dataclass
class HealthCheck:
    category: str
    score: float  # 0-100
    max_score: float
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)


@dataclass
class ListingHealth:
    listing_id: str
    platform: str
    title: str
    overall_score: float
    grade: HealthGrade
    checks: dict = field(default_factory=dict)  # category -> HealthCheck
    alerts: list = field(default_factory=list)
    checked_at: str = ""
    previous_score: Optional[float] = None
    score_change: float = 0.0


@dataclass
class HealthAlert:
    listing_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    details: dict = field(default_factory=dict)
    created_at: str = ""
    resolved: bool = False


class HealthDatabase:
    """SQLite storage for health monitoring data."""

    def __init__(self, db_path: str = "listing_health.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS health_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                title TEXT DEFAULT '',
                overall_score REAL DEFAULT 0.0,
                grade TEXT DEFAULT 'F',
                checks_json TEXT DEFAULT '{}',
                checked_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS health_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                details_json TEXT DEFAULT '{}',
                resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS monitored_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL,
                title TEXT DEFAULT '',
                listing_data TEXT DEFAULT '{}',
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_checked TEXT,
                check_interval_hours INTEGER DEFAULT 24
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_health_listing ON health_snapshots(listing_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_health_time ON health_snapshots(checked_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_alert_listing ON health_alerts(listing_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_alert_severity ON health_alerts(severity)")
        conn.commit()
        conn.close()

    def save_health(self, health: ListingHealth) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        checks_data = {}
        for cat, check in health.checks.items():
            checks_data[cat] = asdict(check)
        c.execute(
            """INSERT INTO health_snapshots
               (listing_id, platform, title, overall_score, grade, checks_json, checked_at)
               VALUES (?,?,?,?,?,?,?)""",
            (health.listing_id, health.platform, health.title,
             health.overall_score, health.grade.value,
             json.dumps(checks_data), health.checked_at),
        )
        row_id = c.lastrowid
        conn.commit()
        conn.close()
        return row_id

    def save_alert(self, alert: HealthAlert) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO health_alerts
               (listing_id, alert_type, severity, message, details_json)
               VALUES (?,?,?,?,?)""",
            (alert.listing_id, alert.alert_type.value, alert.severity.value,
             alert.message, json.dumps(alert.details)),
        )
        row_id = c.lastrowid
        conn.commit()
        conn.close()
        return row_id

    def get_latest_health(self, listing_id: str) -> Optional[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM health_snapshots WHERE listing_id=? ORDER BY checked_at DESC LIMIT 1",
            (listing_id,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_health_history(self, listing_id: str, limit: int = 30) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM health_snapshots WHERE listing_id=? ORDER BY checked_at DESC LIMIT ?",
            (listing_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_active_alerts(self, listing_id: str = None, severity: str = None) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM health_alerts WHERE resolved=0"
        params = []
        if listing_id:
            query += " AND listing_id=?"
            params.append(listing_id)
        if severity:
            query += " AND severity=?"
            params.append(severity)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def resolve_alert(self, alert_id: int):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE health_alerts SET resolved=1, resolved_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), alert_id),
        )
        conn.commit()
        conn.close()

    def add_monitored_listing(self, listing_id: str, platform: str, title: str = "",
                               data: dict = None, interval_hours: int = 24):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO monitored_listings
               (listing_id, platform, title, listing_data, check_interval_hours)
               VALUES (?,?,?,?,?)""",
            (listing_id, platform, title, json.dumps(data or {}), interval_hours),
        )
        conn.commit()
        conn.close()

    def get_due_listings(self) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT * FROM monitored_listings
               WHERE last_checked IS NULL
               OR datetime(last_checked, '+' || check_interval_hours || ' hours') <= datetime('now')"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_checked(self, listing_id: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE monitored_listings SET last_checked=? WHERE listing_id=?",
            (datetime.utcnow().isoformat(), listing_id),
        )
        conn.commit()
        conn.close()

    def get_dashboard_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        total = c.execute("SELECT COUNT(*) FROM monitored_listings").fetchone()[0]
        active_alerts = c.execute("SELECT COUNT(*) FROM health_alerts WHERE resolved=0").fetchone()[0]
        critical = c.execute("SELECT COUNT(*) FROM health_alerts WHERE resolved=0 AND severity='critical'").fetchone()[0]
        avg_score = c.execute(
            """SELECT AVG(overall_score) FROM health_snapshots
               WHERE id IN (SELECT MAX(id) FROM health_snapshots GROUP BY listing_id)"""
        ).fetchone()[0]
        grade_dist = {}
        rows = c.execute(
            """SELECT grade, COUNT(*) FROM health_snapshots
               WHERE id IN (SELECT MAX(id) FROM health_snapshots GROUP BY listing_id)
               GROUP BY grade"""
        ).fetchall()
        for g, cnt in rows:
            grade_dist[g] = cnt
        conn.close()
        return {
            "total_listings": total,
            "active_alerts": active_alerts,
            "critical_alerts": critical,
            "avg_score": round(avg_score, 1) if avg_score else 0,
            "grade_distribution": grade_dist,
        }


class ListingHealthMonitor:
    """Comprehensive listing health checker."""

    TITLE_MIN_LENGTH = 20
    TITLE_MAX_LENGTH = 200
    DESCRIPTION_MIN_LENGTH = 100
    MIN_BULLET_POINTS = 3
    MIN_IMAGES = 3
    KEYWORD_DENSITY_MIN = 0.01
    KEYWORD_DENSITY_MAX = 0.05
    SCORE_DROP_THRESHOLD = 10  # points

    # Platform-specific limits
    PLATFORM_LIMITS = {
        "amazon": {"title_max": 200, "bullets": 5, "desc_max": 2000, "backend_kw": 250, "images": 9},
        "shopee": {"title_max": 120, "bullets": 0, "desc_max": 3000, "backend_kw": 0, "images": 9},
        "lazada": {"title_max": 150, "bullets": 5, "desc_max": 3000, "backend_kw": 0, "images": 8},
        "aliexpress": {"title_max": 128, "bullets": 0, "desc_max": 5000, "backend_kw": 0, "images": 6},
        "ebay": {"title_max": 80, "bullets": 0, "desc_max": 4000, "backend_kw": 0, "images": 12},
        "walmart": {"title_max": 75, "bullets": 5, "desc_max": 4000, "backend_kw": 0, "images": 10},
        "etsy": {"title_max": 140, "bullets": 0, "desc_max": 2000, "backend_kw": 13, "images": 10},
        "temu": {"title_max": 120, "bullets": 0, "desc_max": 2000, "backend_kw": 0, "images": 10},
    }

    PROHIBITED_WORDS = [
        "best", "top", "#1", "number one", "cheapest", "guaranteed",
        "miracle", "cure", "FDA approved", "free", "risk-free",
    ]

    def __init__(self, db: HealthDatabase = None):
        self.db = db or HealthDatabase()

    def check_listing(self, listing_data: dict, platform: str = "amazon") -> ListingHealth:
        """Run all health checks on a listing."""
        listing_id = listing_data.get("id", listing_data.get("asin", "unknown"))
        title = listing_data.get("title", "")
        now = datetime.utcnow().isoformat()

        checks = {}
        checks["title"] = self._check_title(listing_data, platform)
        checks["description"] = self._check_description(listing_data, platform)
        checks["seo"] = self._check_seo(listing_data, platform)
        checks["images"] = self._check_images(listing_data, platform)
        checks["pricing"] = self._check_pricing(listing_data, platform)
        checks["compliance"] = self._check_compliance(listing_data, platform)
        checks["content_quality"] = self._check_content_quality(listing_data, platform)
        checks["completeness"] = self._check_completeness(listing_data, platform)

        total_score = sum(c.score for c in checks.values())
        max_score = sum(c.max_score for c in checks.values())
        overall = (total_score / max_score * 100) if max_score > 0 else 0
        grade = self._score_to_grade(overall)

        # Check for score drop
        previous = self.db.get_latest_health(listing_id)
        previous_score = None
        score_change = 0.0
        if previous:
            previous_score = previous["overall_score"]
            score_change = overall - previous_score

        health = ListingHealth(
            listing_id=listing_id,
            platform=platform,
            title=title,
            overall_score=round(overall, 1),
            grade=grade,
            checks=checks,
            alerts=[],
            checked_at=now,
            previous_score=previous_score,
            score_change=round(score_change, 1),
        )

        # Generate alerts
        alerts = self._generate_alerts(health, checks)
        health.alerts = [asdict(a) for a in alerts]

        # Save
        self.db.save_health(health)
        for alert in alerts:
            self.db.save_alert(alert)

        return health

    def _check_title(self, data: dict, platform: str) -> HealthCheck:
        title = data.get("title", "")
        limits = self.PLATFORM_LIMITS.get(platform, self.PLATFORM_LIMITS["amazon"])
        issues = []
        suggestions = []
        score = 20.0

        if not title:
            return HealthCheck("title", 0, 20, ["Missing title"], ["Add a descriptive product title"])

        if len(title) < self.TITLE_MIN_LENGTH:
            issues.append(f"Title too short ({len(title)} chars)")
            suggestions.append(f"Expand title to at least {self.TITLE_MIN_LENGTH} chars with keywords")
            score -= 8

        if len(title) > limits["title_max"]:
            issues.append(f"Title exceeds {platform} limit ({len(title)}/{limits['title_max']})")
            suggestions.append(f"Trim title to {limits['title_max']} characters")
            score -= 10

        if title == title.upper() and len(title) > 5:
            issues.append("Title is ALL CAPS")
            suggestions.append("Use Title Case for better readability")
            score -= 5

        if title == title.lower():
            issues.append("Title has no capitalization")
            suggestions.append("Capitalize important words")
            score -= 3

        # Check for keyword stuffing (repeated words)
        words = title.lower().split()
        if words:
            word_freq = {}
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
            max_freq = max(word_freq.values())
            if max_freq > 3 and len(words) > 5:
                issues.append("Possible keyword stuffing in title")
                suggestions.append("Reduce repeated words for natural readability")
                score -= 5

        return HealthCheck("title", max(0, score), 20, issues, suggestions)

    def _check_description(self, data: dict, platform: str) -> HealthCheck:
        desc = data.get("description", "")
        bullets = data.get("bullet_points", [])
        limits = self.PLATFORM_LIMITS.get(platform, self.PLATFORM_LIMITS["amazon"])
        issues = []
        suggestions = []
        score = 20.0

        if not desc:
            issues.append("Missing product description")
            suggestions.append("Add a detailed product description")
            score -= 15

        if desc and len(desc) < self.DESCRIPTION_MIN_LENGTH:
            issues.append(f"Description too short ({len(desc)} chars)")
            suggestions.append(f"Expand description to at least {self.DESCRIPTION_MIN_LENGTH} chars")
            score -= 8

        if limits.get("bullets", 0) > 0:
            if not bullets:
                issues.append("Missing bullet points")
                suggestions.append(f"Add {limits['bullets']} benefit-focused bullet points")
                score -= 8
            elif len(bullets) < self.MIN_BULLET_POINTS:
                issues.append(f"Only {len(bullets)} bullet points (min {self.MIN_BULLET_POINTS})")
                suggestions.append(f"Add {self.MIN_BULLET_POINTS - len(bullets)} more bullet points")
                score -= 4

        if desc and len(desc) > limits.get("desc_max", 4000):
            issues.append("Description exceeds platform limit")
            suggestions.append(f"Trim to {limits['desc_max']} characters")
            score -= 5

        return HealthCheck("description", max(0, score), 20, issues, suggestions)

    def _check_seo(self, data: dict, platform: str) -> HealthCheck:
        title = data.get("title", "")
        desc = data.get("description", "")
        keywords = data.get("keywords", [])
        backend_kw = data.get("backend_keywords", "")
        limits = self.PLATFORM_LIMITS.get(platform, self.PLATFORM_LIMITS["amazon"])
        issues = []
        suggestions = []
        score = 15.0

        if not keywords:
            issues.append("No target keywords defined")
            suggestions.append("Research and add 5-10 relevant keywords")
            score -= 8

        if keywords and title:
            title_lower = title.lower()
            primary_kw = keywords[0].lower() if keywords else ""
            if primary_kw and primary_kw not in title_lower:
                issues.append("Primary keyword not in title")
                suggestions.append(f"Include '{keywords[0]}' in the title")
                score -= 5

        if limits.get("backend_kw", 0) > 0:
            if not backend_kw:
                issues.append("Missing backend/search keywords")
                suggestions.append("Add backend keywords for search visibility")
                score -= 4
            elif len(backend_kw) > limits["backend_kw"]:
                issues.append(f"Backend keywords too long ({len(backend_kw)}/{limits['backend_kw']})")
                score -= 3

        # Keyword density check
        if keywords and desc:
            text = (title + " " + desc).lower()
            total_words = len(text.split())
            if total_words > 0:
                for kw in keywords[:3]:
                    count = text.count(kw.lower())
                    density = count / total_words
                    if density > self.KEYWORD_DENSITY_MAX:
                        issues.append(f"Keyword '{kw}' density too high ({density:.1%})")
                        suggestions.append(f"Reduce '{kw}' usage to avoid penalty")
                        score -= 2

        return HealthCheck("seo", max(0, score), 15, issues, suggestions)

    def _check_images(self, data: dict, platform: str) -> HealthCheck:
        images = data.get("images", [])
        limits = self.PLATFORM_LIMITS.get(platform, self.PLATFORM_LIMITS["amazon"])
        issues = []
        suggestions = []
        score = 15.0

        if not images:
            issues.append("No product images")
            suggestions.append(f"Add at least {self.MIN_IMAGES} high-quality images")
            score -= 15
        elif len(images) < self.MIN_IMAGES:
            issues.append(f"Only {len(images)} images (recommended: {limits.get('images', 6)}+)")
            suggestions.append("Add lifestyle, detail, and comparison images")
            score -= 7

        # Check image attributes if available
        for i, img in enumerate(images):
            if isinstance(img, dict):
                width = img.get("width", 0)
                height = img.get("height", 0)
                if width > 0 and height > 0 and (width < 1000 or height < 1000):
                    issues.append(f"Image {i+1} resolution too low ({width}x{height})")
                    suggestions.append(f"Use at least 1000x1000px for image {i+1}")
                    score -= 2
                if not img.get("alt_text", ""):
                    issues.append(f"Image {i+1} missing alt text")
                    score -= 1

        return HealthCheck("images", max(0, score), 15, issues, suggestions)

    def _check_pricing(self, data: dict, platform: str) -> HealthCheck:
        price = data.get("price", 0)
        compare_price = data.get("compare_price", 0)
        cost = data.get("cost", 0)
        issues = []
        suggestions = []
        score = 10.0

        if not price or price <= 0:
            issues.append("No price set")
            score -= 10
        else:
            if compare_price and compare_price > 0:
                discount = (compare_price - price) / compare_price * 100
                if discount > 70:
                    issues.append(f"Unrealistic discount ({discount:.0f}%)")
                    suggestions.append("Reduce compare-at price to maintain credibility")
                    score -= 5
                elif discount < 0:
                    issues.append("Sale price higher than compare price")
                    score -= 3

            if cost and cost > 0:
                margin = (price - cost) / price * 100
                if margin < 0:
                    issues.append("Selling below cost!")
                    score -= 8
                elif margin < 20:
                    issues.append(f"Low profit margin ({margin:.0f}%)")
                    suggestions.append("Consider raising price or reducing costs")
                    score -= 3

            if price < 1:
                issues.append("Suspiciously low price")
                score -= 5

        return HealthCheck("pricing", max(0, score), 10, issues, suggestions)

    def _check_compliance(self, data: dict, platform: str) -> HealthCheck:
        title = data.get("title", "")
        desc = data.get("description", "")
        text = (title + " " + desc).lower()
        issues = []
        suggestions = []
        score = 10.0

        for word in self.PROHIBITED_WORDS:
            if word.lower() in text:
                issues.append(f"Prohibited/risky word: '{word}'")
                suggestions.append(f"Remove or rephrase '{word}' to avoid policy violations")
                score -= 2

        # Check for missing required fields
        if not data.get("category"):
            issues.append("No product category set")
            suggestions.append("Select appropriate product category")
            score -= 2

        if not data.get("brand") and platform in ("amazon", "walmart"):
            issues.append("Missing brand name")
            suggestions.append("Add brand information")
            score -= 2

        return HealthCheck("compliance", max(0, score), 10, issues, suggestions)

    def _check_content_quality(self, data: dict, platform: str) -> HealthCheck:
        title = data.get("title", "")
        desc = data.get("description", "")
        issues = []
        suggestions = []
        score = 5.0

        # Check for common quality issues
        if desc:
            sentences = desc.split(".")
            short_sentences = [s for s in sentences if len(s.strip()) > 0 and len(s.strip()) < 10]
            if len(short_sentences) > len(sentences) * 0.5 and len(sentences) > 3:
                issues.append("Many very short sentences - may appear low quality")
                suggestions.append("Elaborate on product features and benefits")
                score -= 2

            if "lorem ipsum" in desc.lower() or "placeholder" in desc.lower():
                issues.append("Placeholder text detected!")
                suggestions.append("Replace with actual product description")
                score -= 5

        # Emoji check for relevant platforms
        if platform in ("shopee", "lazada", "temu") and desc:
            import re
            emoji_pattern = re.compile(
                "[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]"
            )
            if not emoji_pattern.search(desc):
                suggestions.append("Consider adding emojis for Southeast Asian marketplace appeal")
                score -= 1

        return HealthCheck("content_quality", max(0, score), 5, issues, suggestions)

    def _check_completeness(self, data: dict, platform: str) -> HealthCheck:
        issues = []
        suggestions = []
        score = 5.0

        required_fields = ["title", "description", "price", "images"]
        recommended_fields = ["keywords", "category", "brand", "sku", "weight"]

        for f in required_fields:
            val = data.get(f)
            if not val or (isinstance(val, (list, dict)) and len(val) == 0):
                issues.append(f"Missing required field: {f}")
                score -= 1.25

        missing_recommended = []
        for f in recommended_fields:
            val = data.get(f)
            if not val or (isinstance(val, (list, dict)) and len(val) == 0):
                missing_recommended.append(f)

        if missing_recommended:
            suggestions.append(f"Consider adding: {', '.join(missing_recommended)}")
            score -= min(2, len(missing_recommended) * 0.4)

        return HealthCheck("completeness", max(0, score), 5, issues, suggestions)

    def _score_to_grade(self, score: float) -> HealthGrade:
        if score >= 95:
            return HealthGrade.A_PLUS
        elif score >= 85:
            return HealthGrade.A
        elif score >= 70:
            return HealthGrade.B
        elif score >= 55:
            return HealthGrade.C
        elif score >= 40:
            return HealthGrade.D
        return HealthGrade.F

    def _generate_alerts(self, health: ListingHealth, checks: dict) -> list[HealthAlert]:
        alerts = []

        # Score drop alert
        if health.previous_score is not None and health.score_change < -self.SCORE_DROP_THRESHOLD:
            alerts.append(HealthAlert(
                listing_id=health.listing_id,
                alert_type=AlertType.SCORE_DROP,
                severity=AlertSeverity.WARNING,
                message=f"Health score dropped by {abs(health.score_change):.1f} points "
                        f"({health.previous_score:.1f} → {health.overall_score:.1f})",
                details={"previous": health.previous_score, "current": health.overall_score},
                created_at=health.checked_at,
            ))

        # Critical grade alert
        if health.grade in (HealthGrade.D, HealthGrade.F):
            alerts.append(HealthAlert(
                listing_id=health.listing_id,
                alert_type=AlertType.CONTENT_QUALITY,
                severity=AlertSeverity.CRITICAL,
                message=f"Listing grade is {health.grade.value} — needs immediate attention",
                created_at=health.checked_at,
            ))

        # Check-specific alerts
        for cat, check in checks.items():
            if check.score == 0 and check.max_score > 0:
                alerts.append(HealthAlert(
                    listing_id=health.listing_id,
                    alert_type=AlertType.MISSING_FIELD,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Category '{cat}' scored 0/{check.max_score} — critical issues found",
                    details={"issues": check.issues},
                    created_at=health.checked_at,
                ))
            elif check.issues and check.score < check.max_score * 0.5:
                alerts.append(HealthAlert(
                    listing_id=health.listing_id,
                    alert_type=AlertType.CONTENT_QUALITY,
                    severity=AlertSeverity.WARNING,
                    message=f"Category '{cat}' needs improvement: {check.issues[0]}",
                    details={"issues": check.issues, "score": check.score},
                    created_at=health.checked_at,
                ))

        return alerts

    def batch_check(self, listings: list[dict], platform: str = "amazon") -> list[ListingHealth]:
        """Check multiple listings at once."""
        results = []
        for listing in listings:
            health = self.check_listing(listing, platform)
            results.append(health)
        return sorted(results, key=lambda h: h.overall_score)

    def format_health_report(self, health: ListingHealth) -> str:
        """Format health check as readable text."""
        grade_emoji = {
            "A+": "🏆", "A": "✅", "B": "👍",
            "C": "⚠️", "D": "❌", "F": "🚨",
        }
        lines = [
            f"{grade_emoji.get(health.grade.value, '📊')} Listing Health: {health.grade.value} ({health.overall_score:.1f}/100)",
            f"Platform: {health.platform.upper()} | ID: {health.listing_id}",
            f"Title: {health.title[:60]}{'...' if len(health.title) > 60 else ''}",
        ]

        if health.previous_score is not None:
            arrow = "↗️" if health.score_change > 0 else "↘️" if health.score_change < 0 else "➡️"
            lines.append(f"Trend: {arrow} {health.score_change:+.1f} from last check")

        lines.append("")
        for cat, check in health.checks.items():
            pct = (check.score / check.max_score * 100) if check.max_score > 0 else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            lines.append(f"  {cat:18s} [{bar}] {check.score:.0f}/{check.max_score:.0f}")
            for issue in check.issues:
                lines.append(f"    ⚠️ {issue}")
            for sug in check.suggestions[:2]:
                lines.append(f"    💡 {sug}")

        if health.alerts:
            lines.append("")
            lines.append("🔔 Alerts:")
            for a in health.alerts:
                sev_icon = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
                lines.append(f"  {sev_icon.get(a.get('severity','info'))} {a.get('message','')}")

        return "\n".join(lines)

    def format_batch_summary(self, results: list[ListingHealth]) -> str:
        """Format batch check summary."""
        if not results:
            return "No listings checked."

        lines = ["📊 Batch Health Report", f"Listings checked: {len(results)}", ""]

        grades: dict[str, int] = {}
        total_score = 0
        for r in results:
            grades[r.grade.value] = grades.get(r.grade.value, 0) + 1
            total_score += r.overall_score
        avg = total_score / len(results)

        lines.append(f"Average score: {avg:.1f}/100")
        lines.append("Grade distribution: " + " | ".join(f"{g}: {c}" for g, c in sorted(grades.items())))
        lines.append("")

        # Worst listings
        worst = sorted(results, key=lambda r: r.overall_score)[:5]
        if worst:
            lines.append("⚠️ Needs Attention:")
            for w in worst:
                lines.append(f"  {w.grade.value} {w.overall_score:.0f}pts | {w.listing_id} | {w.title[:40]}")

        # Best listings
        best = sorted(results, key=lambda r: r.overall_score, reverse=True)[:3]
        if best:
            lines.append("")
            lines.append("✅ Top Performers:")
            for b in best:
                lines.append(f"  {b.grade.value} {b.overall_score:.0f}pts | {b.listing_id} | {b.title[:40]}")

        total_alerts = sum(len(r.alerts) for r in results)
        critical = sum(1 for r in results for a in r.alerts if a.get("severity") == "critical")
        lines.append("")
        lines.append(f"Total alerts: {total_alerts} ({critical} critical)")

        return "\n".join(lines)
