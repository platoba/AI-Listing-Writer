"""Seasonal listing optimizer.

Optimizes product listings based on:
- Seasonal trends (spring/summer/fall/winter)
- Holiday keywords and themes (Black Friday, Christmas, Prime Day, etc.)
- Monthly search volume patterns
- Event-based optimization windows
- Regional seasonal differences
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


# Seasonal keyword modifiers
SEASONAL_KEYWORDS = {
    "spring": {
        "months": [3, 4, 5],
        "keywords": [
            "spring", "fresh", "new season", "renewal", "bloom", "garden",
            "outdoor", "lightweight", "pastel", "allergy", "cleaning",
            "spring cleaning", "easter", "mother's day", "graduation",
            "春季", "春天", "清新", "轻薄", "换季",
        ],
        "themes": ["renewal", "fresh start", "outdoor activity", "cleaning"],
        "colors": ["pastel green", "light blue", "pink", "yellow", "lavender"],
    },
    "summer": {
        "months": [6, 7, 8],
        "keywords": [
            "summer", "beach", "outdoor", "sun", "UV", "sunscreen",
            "cooling", "portable", "travel", "vacation", "waterproof",
            "lightweight", "breathable", "pool", "camping", "BBQ",
            "4th of july", "independence day", "back to school",
            "夏季", "防晒", "清凉", "户外", "旅行", "便携",
        ],
        "themes": ["outdoor fun", "travel", "staying cool", "water activities"],
        "colors": ["bright blue", "coral", "white", "turquoise", "neon"],
    },
    "fall": {
        "months": [9, 10, 11],
        "keywords": [
            "fall", "autumn", "cozy", "warm", "harvest", "pumpkin",
            "thanksgiving", "halloween", "back to school", "layering",
            "flannel", "sweater", "rustic", "comfort", "seasonal",
            "black friday", "cyber monday", "prime day",
            "秋季", "保暖", "舒适", "温暖",
        ],
        "themes": ["cozy comfort", "warmth", "harvest", "holiday prep"],
        "colors": ["burnt orange", "deep red", "gold", "brown", "forest green"],
    },
    "winter": {
        "months": [12, 1, 2],
        "keywords": [
            "winter", "warm", "insulated", "thermal", "cold weather",
            "snow", "holiday", "christmas", "gift", "new year",
            "valentine", "cozy", "heated", "waterproof", "wind-proof",
            "stocking stuffer", "gift guide", "white elephant",
            "冬季", "保暖", "圣诞", "新年", "礼物", "加厚",
        ],
        "themes": ["gift giving", "warmth", "holiday celebration", "indoor"],
        "colors": ["deep blue", "red", "gold", "silver", "white", "emerald"],
    },
}

# Major shopping events
SHOPPING_EVENTS = [
    {
        "name": "New Year Sales",
        "month": 1, "day_start": 1, "day_end": 7,
        "keywords": ["new year", "sale", "clearance", "2026", "resolution"],
        "boost": 1.3,
    },
    {
        "name": "Valentine's Day",
        "month": 2, "day_start": 1, "day_end": 14,
        "keywords": ["valentine", "gift for her", "gift for him", "love",
                      "romantic", "couples", "heart"],
        "boost": 1.5,
    },
    {
        "name": "International Women's Day",
        "month": 3, "day_start": 1, "day_end": 8,
        "keywords": ["women", "her", "empowerment", "self-care", "beauty"],
        "boost": 1.2,
    },
    {
        "name": "Easter",
        "month": 4, "day_start": 1, "day_end": 20,
        "keywords": ["easter", "spring", "bunny", "pastel", "gift basket"],
        "boost": 1.2,
    },
    {
        "name": "Mother's Day",
        "month": 5, "day_start": 1, "day_end": 12,
        "keywords": ["mother's day", "mom", "gift for mom", "mama",
                      "motherhood", "appreciation"],
        "boost": 1.5,
    },
    {
        "name": "Father's Day",
        "month": 6, "day_start": 1, "day_end": 15,
        "keywords": ["father's day", "dad", "gift for dad", "papa",
                      "fatherhood"],
        "boost": 1.4,
    },
    {
        "name": "Prime Day",
        "month": 7, "day_start": 10, "day_end": 17,
        "keywords": ["prime day", "deal", "limited time", "exclusive",
                      "lightning deal", "save"],
        "boost": 2.0,
    },
    {
        "name": "Back to School",
        "month": 8, "day_start": 1, "day_end": 31,
        "keywords": ["back to school", "school supplies", "student",
                      "college", "dorm", "study", "backpack"],
        "boost": 1.5,
    },
    {
        "name": "Halloween",
        "month": 10, "day_start": 1, "day_end": 31,
        "keywords": ["halloween", "costume", "spooky", "trick or treat",
                      "decoration", "pumpkin", "scary"],
        "boost": 1.4,
    },
    {
        "name": "Singles Day (11.11)",
        "month": 11, "day_start": 1, "day_end": 11,
        "keywords": ["singles day", "11.11", "double eleven", "mega sale",
                      "双十一", "光棍节"],
        "boost": 1.8,
    },
    {
        "name": "Black Friday",
        "month": 11, "day_start": 20, "day_end": 30,
        "keywords": ["black friday", "deal", "doorbuster", "limited",
                      "save", "discount", "lowest price"],
        "boost": 2.0,
    },
    {
        "name": "Cyber Monday",
        "month": 12, "day_start": 1, "day_end": 3,
        "keywords": ["cyber monday", "online deal", "flash sale",
                      "free shipping", "digital"],
        "boost": 1.8,
    },
    {
        "name": "Christmas",
        "month": 12, "day_start": 1, "day_end": 25,
        "keywords": ["christmas", "holiday", "gift", "present", "stocking",
                      "xmas", "festive", "santa", "ornament"],
        "boost": 2.0,
    },
    {
        "name": "Year-End Clearance",
        "month": 12, "day_start": 26, "day_end": 31,
        "keywords": ["clearance", "year-end", "final sale", "last chance",
                      "closeout"],
        "boost": 1.5,
    },
]

# Product category seasonal peaks
CATEGORY_SEASONALITY = {
    "outdoor": {"peak": "summer", "low": "winter"},
    "fitness": {"peak": "winter", "low": "summer"},  # New Year resolutions
    "garden": {"peak": "spring", "low": "winter"},
    "fashion": {"peak": None, "low": None},  # All-season, trend-driven
    "electronics": {"peak": "winter", "low": "spring"},  # Holiday gifts
    "home": {"peak": "spring", "low": "summer"},  # Spring cleaning
    "toys": {"peak": "winter", "low": "spring"},
    "beauty": {"peak": "winter", "low": None},
    "sports": {"peak": "summer", "low": "winter"},
    "food": {"peak": "winter", "low": None},  # Holiday cooking
    "pet": {"peak": None, "low": None},  # Steady
    "baby": {"peak": None, "low": None},
    "automotive": {"peak": "fall", "low": "spring"},
    "office": {"peak": "fall", "low": "summer"},  # Back to school
}


@dataclass
class SeasonalKeywordSuggestion:
    """A suggested seasonal keyword to add to listing."""
    keyword: str
    relevance: float  # 0-1
    reason: str
    category: str  # season or event name
    urgency: str  # "now", "upcoming", "plan_ahead"


@dataclass
class SeasonalOptimization:
    """Complete seasonal optimization result."""
    current_season: str
    current_events: list[str] = field(default_factory=list)
    upcoming_events: list[str] = field(default_factory=list)

    keyword_suggestions: list[SeasonalKeywordSuggestion] = field(default_factory=list)
    title_suggestions: list[str] = field(default_factory=list)
    bullet_suggestions: list[str] = field(default_factory=list)
    color_suggestions: list[str] = field(default_factory=list)

    category_timing: str = ""  # "peak", "low", "normal"
    optimization_score: float = 0.0  # 0-100
    action_items: list[str] = field(default_factory=list)

    @property
    def is_peak_season(self) -> bool:
        return self.category_timing == "peak"


class SeasonalOptimizer:
    """Optimize listings for seasonal trends and shopping events."""

    def __init__(self, reference_date: Optional[date] = None):
        self.ref_date = reference_date or date.today()
        self.current_month = self.ref_date.month
        self.current_season = self._get_season(self.current_month)

    def optimize(
        self,
        title: str,
        bullets: list[str],
        description: str = "",
        category: str = "",
        target_keywords: Optional[list[str]] = None,
    ) -> SeasonalOptimization:
        """Run seasonal optimization on a listing."""
        result = SeasonalOptimization(current_season=self.current_season)
        listing_text = f"{title} {' '.join(bullets)} {description}".lower()

        # 1. Find current and upcoming events
        result.current_events = self._get_current_events()
        result.upcoming_events = self._get_upcoming_events()

        # 2. Check category seasonality
        if category:
            result.category_timing = self._check_category_timing(category)

        # 3. Generate keyword suggestions
        result.keyword_suggestions = self._suggest_keywords(
            listing_text, category, target_keywords or []
        )

        # 4. Generate title suggestions
        result.title_suggestions = self._suggest_title_mods(title, category)

        # 5. Generate bullet suggestions
        result.bullet_suggestions = self._suggest_bullet_additions(
            bullets, category
        )

        # 6. Color suggestions
        season_data = SEASONAL_KEYWORDS.get(self.current_season, {})
        result.color_suggestions = season_data.get("colors", [])

        # 7. Calculate optimization score
        result.optimization_score = self._calculate_score(listing_text, result)

        # 8. Action items
        result.action_items = self._generate_actions(result, category)

        return result

    def _get_season(self, month: int) -> str:
        """Determine season from month."""
        for season, data in SEASONAL_KEYWORDS.items():
            if month in data["months"]:
                return season
        return "spring"  # fallback

    def _get_current_events(self) -> list[str]:
        """Get shopping events active right now."""
        events = []
        for event in SHOPPING_EVENTS:
            if (event["month"] == self.current_month and
                    event["day_start"] <= self.ref_date.day <= event["day_end"]):
                events.append(event["name"])
        return events

    def _get_upcoming_events(self, lookahead_days: int = 45) -> list[str]:
        """Get shopping events coming in the next N days."""
        events = []
        for event in SHOPPING_EVENTS:
            try:
                event_start = date(
                    self.ref_date.year, event["month"], event["day_start"]
                )
            except ValueError:
                continue

            delta = (event_start - self.ref_date).days
            if 0 < delta <= lookahead_days:
                events.append(f"{event['name']} (in {delta} days)")
        return events

    def _check_category_timing(self, category: str) -> str:
        """Check if current season is peak/low for category."""
        cat_lower = category.lower()
        for cat_key, timing in CATEGORY_SEASONALITY.items():
            if cat_key in cat_lower:
                if timing["peak"] == self.current_season:
                    return "peak"
                if timing["low"] == self.current_season:
                    return "low"
                return "normal"
        return "normal"

    def _suggest_keywords(
        self,
        listing_text: str,
        category: str,
        existing_keywords: list[str],
    ) -> list[SeasonalKeywordSuggestion]:
        """Suggest seasonal keywords to add."""
        suggestions = []
        existing_lower = {kw.lower() for kw in existing_keywords}

        # Current season keywords
        season_data = SEASONAL_KEYWORDS.get(self.current_season, {})
        for kw in season_data.get("keywords", []):
            if kw.lower() not in listing_text and kw.lower() not in existing_lower:
                suggestions.append(SeasonalKeywordSuggestion(
                    keyword=kw,
                    relevance=0.7,
                    reason=f"Trending for {self.current_season} season",
                    category=self.current_season,
                    urgency="now",
                ))

        # Current event keywords
        for event in SHOPPING_EVENTS:
            if (event["month"] == self.current_month and
                    event["day_start"] <= self.ref_date.day <= event["day_end"]):
                for kw in event["keywords"]:
                    if kw.lower() not in listing_text:
                        suggestions.append(SeasonalKeywordSuggestion(
                            keyword=kw,
                            relevance=min(1.0, 0.5 * event["boost"]),
                            reason=f"Active event: {event['name']}",
                            category=event["name"],
                            urgency="now",
                        ))

        # Upcoming event keywords (prep ahead)
        for event in SHOPPING_EVENTS:
            try:
                event_start = date(
                    self.ref_date.year, event["month"], event["day_start"]
                )
            except ValueError:
                continue
            delta = (event_start - self.ref_date).days
            if 14 < delta <= 45:
                for kw in event["keywords"][:3]:
                    if kw.lower() not in listing_text:
                        suggestions.append(SeasonalKeywordSuggestion(
                            keyword=kw,
                            relevance=0.5,
                            reason=f"Prepare for {event['name']} ({delta} days away)",
                            category=event["name"],
                            urgency="plan_ahead",
                        ))

        # Sort by relevance
        suggestions.sort(key=lambda s: s.relevance, reverse=True)
        return suggestions[:20]

    def _suggest_title_mods(self, title: str, category: str) -> list[str]:
        """Suggest title modifications for seasonal optimization."""
        suggestions = []
        title_lower = title.lower()

        season_data = SEASONAL_KEYWORDS.get(self.current_season, {})
        themes = season_data.get("themes", [])

        # Check if title already has seasonal keywords
        has_seasonal = any(
            kw in title_lower
            for kw in season_data.get("keywords", [])[:5]
        )

        if not has_seasonal:
            season_cap = self.current_season.capitalize()
            suggestions.append(
                f"Add '{season_cap}' or seasonal keyword to title for "
                f"seasonal search visibility"
            )

        # Event-specific title suggestions
        for event in self._get_current_events():
            event_lower = event.lower()
            if event_lower not in title_lower:
                suggestions.append(
                    f"Consider adding '{event}' to title during this "
                    f"shopping event window"
                )

        # Theme suggestions
        if themes:
            suggestions.append(
                f"Emphasize {self.current_season} themes: "
                f"{', '.join(themes[:3])}"
            )

        return suggestions[:5]

    def _suggest_bullet_additions(
        self, bullets: list[str], category: str
    ) -> list[str]:
        """Suggest new bullet points for seasonal relevance."""
        suggestions = []
        bullet_text = " ".join(b.lower() for b in bullets)

        season_data = SEASONAL_KEYWORDS.get(self.current_season, {})
        themes = season_data.get("themes", [])

        for theme in themes:
            if theme not in bullet_text:
                suggestions.append(
                    f"Add bullet highlighting '{theme}' — "
                    f"relevant for {self.current_season} shoppers"
                )

        # Gift-giving season
        if self.current_season == "winter" and "gift" not in bullet_text:
            suggestions.append(
                "🎁 Add 'Perfect gift for...' bullet — "
                "peak gift-buying season"
            )

        # Back to school
        if self.current_month in [7, 8] and "school" not in bullet_text:
            if category and any(c in category.lower()
                                for c in ["office", "electronics", "bags"]):
                suggestions.append(
                    "🎒 Add 'Great for back-to-school' bullet"
                )

        return suggestions[:5]

    def _calculate_score(
        self, listing_text: str, result: SeasonalOptimization
    ) -> float:
        """Calculate seasonal optimization score (0-100)."""
        score = 50.0  # Base

        season_data = SEASONAL_KEYWORDS.get(self.current_season, {})
        season_keywords = season_data.get("keywords", [])

        # +points for seasonal keywords found in listing
        found = sum(1 for kw in season_keywords if kw in listing_text)
        keyword_score = min(30, found * 5)
        score += keyword_score

        # +points for event-relevant content
        if result.current_events:
            for event in SHOPPING_EVENTS:
                if event["name"] in result.current_events:
                    found_event_kw = sum(
                        1 for kw in event["keywords"]
                        if kw in listing_text
                    )
                    score += min(15, found_event_kw * 3)

        # -points for too many missing suggestions
        missing = len(result.keyword_suggestions)
        score -= min(20, missing * 1)

        # Peak season bonus / penalty
        if result.category_timing == "peak":
            score += 5
        elif result.category_timing == "low":
            score -= 10

        return round(max(0, min(100, score)), 1)

    def _generate_actions(
        self, result: SeasonalOptimization, category: str
    ) -> list[str]:
        """Generate prioritized action items."""
        actions = []

        # Urgent: current events
        if result.current_events:
            events_str = ", ".join(result.current_events)
            actions.append(
                f"🔴 URGENT: Optimize for active events: {events_str}"
            )

        # Upcoming events
        if result.upcoming_events:
            actions.append(
                f"🟡 PREPARE: Upcoming events: "
                f"{', '.join(result.upcoming_events[:3])}"
            )

        # Peak season
        if result.is_peak_season:
            actions.append(
                f"🟢 CAPITALIZE: Peak season for {category or 'your category'} — "
                f"maximize ad spend and inventory"
            )

        # Low score
        if result.optimization_score < 40:
            actions.append(
                "🔴 LOW SCORE: Listing needs significant seasonal optimization"
            )

        # Keyword additions
        urgent_kw = [k for k in result.keyword_suggestions if k.urgency == "now"]
        if urgent_kw:
            top_kw = ", ".join(k.keyword for k in urgent_kw[:5])
            actions.append(f"📝 ADD KEYWORDS: {top_kw}")

        return actions


def optimize_for_season(
    title: str,
    bullets: list[str],
    description: str = "",
    category: str = "",
    reference_date: Optional[date] = None,
) -> SeasonalOptimization:
    """Convenience function for seasonal optimization."""
    optimizer = SeasonalOptimizer(reference_date=reference_date)
    return optimizer.optimize(title, bullets, description, category)


def format_seasonal_report(opt: SeasonalOptimization) -> str:
    """Format seasonal optimization as readable report."""
    lines = [
        "=" * 60,
        "🌿 SEASONAL OPTIMIZATION REPORT",
        "=" * 60,
        "",
        f"Current Season: {opt.current_season.upper()}",
        f"Optimization Score: {opt.optimization_score}/100",
        f"Category Timing: {opt.category_timing}",
        "",
    ]

    if opt.current_events:
        lines.append("🔥 Active Shopping Events:")
        for e in opt.current_events:
            lines.append(f"  • {e}")
        lines.append("")

    if opt.upcoming_events:
        lines.append("📅 Upcoming Events:")
        for e in opt.upcoming_events:
            lines.append(f"  • {e}")
        lines.append("")

    if opt.keyword_suggestions:
        lines.append("🔑 Suggested Keywords:")
        for kw in opt.keyword_suggestions[:10]:
            icon = "🔴" if kw.urgency == "now" else "🟡" if kw.urgency == "upcoming" else "🔵"
            lines.append(f"  {icon} {kw.keyword} — {kw.reason}")
        lines.append("")

    if opt.title_suggestions:
        lines.append("📝 Title Suggestions:")
        for s in opt.title_suggestions:
            lines.append(f"  • {s}")
        lines.append("")

    if opt.bullet_suggestions:
        lines.append("📋 Bullet Point Suggestions:")
        for s in opt.bullet_suggestions:
            lines.append(f"  • {s}")
        lines.append("")

    if opt.color_suggestions:
        lines.append(f"🎨 Seasonal Colors: {', '.join(opt.color_suggestions)}")
        lines.append("")

    if opt.action_items:
        lines.append("⚡ Action Items:")
        for a in opt.action_items:
            lines.append(f"  {a}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
