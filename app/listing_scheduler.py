"""
Listing Update Scheduler
========================

Optimal listing update timing and scheduling engine.

Features:
- Platform-specific optimal update windows
- Timezone-aware scheduling across marketplaces
- Holiday / peak season calendar
- Update priority scoring (which listing to update first)
- Cooldown management (avoid too-frequent updates)
- Batch update planning
- A/B test scheduling
- Performance-based auto-scheduling
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


# ── Models ───────────────────────────────────────────────────

class UpdatePriority(str, Enum):
    CRITICAL = "critical"  # Compliance issue, listing suppressed
    HIGH = "high"          # Significant improvement opportunity
    MEDIUM = "medium"      # Optimization tweak
    LOW = "low"            # Minor refinement
    NONE = "none"          # No update needed


class UpdateType(str, Enum):
    TITLE = "title"
    BULLETS = "bullets"
    DESCRIPTION = "description"
    IMAGES = "images"
    KEYWORDS = "keywords"
    PRICING = "pricing"
    FULL = "full"
    AB_TEST = "ab_test"


@dataclass
class TimeWindow:
    """Optimal time window for updates."""
    day_of_week: int  # 0=Monday, 6=Sunday
    hour_start: int   # 0-23
    hour_end: int      # 0-23
    timezone: str
    score: float       # 0-1 effectiveness
    reason: str = ""

    @property
    def day_name(self) -> str:
        return ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"][self.day_of_week]


@dataclass
class ScheduledUpdate:
    """A scheduled listing update."""
    listing_id: str
    platform: str
    update_type: UpdateType
    priority: UpdatePriority
    scheduled_at: datetime
    window: Optional[TimeWindow] = None
    content: dict = field(default_factory=dict)
    status: str = "pending"  # pending, in_progress, completed, failed, skipped
    created_at: datetime = field(default_factory=datetime.now)
    notes: str = ""

    @property
    def is_overdue(self) -> bool:
        return self.status == "pending" and datetime.now() > self.scheduled_at


@dataclass
class UpdatePlan:
    """Batch update execution plan."""
    updates: list[ScheduledUpdate]
    total_count: int
    estimated_duration_min: float
    risk_level: str  # low, medium, high
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"📋 Update Plan ({self.total_count} updates)",
            f"⏱️ Estimated duration: {self.estimated_duration_min:.0f} minutes",
            f"⚠️ Risk level: {self.risk_level}",
        ]
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚡ {w}")
        lines.append("")
        for u in self.updates:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡",
                    "low": "🟢", "none": "⚪"}.get(u.priority.value, "⚪")
            lines.append(
                f"  {icon} [{u.platform}] {u.listing_id} — "
                f"{u.update_type.value} @ {u.scheduled_at:%Y-%m-%d %H:%M}"
            )
        return "\n".join(lines)


# ── Platform Optimal Windows ────────────────────────────────

PLATFORM_WINDOWS: dict[str, list[TimeWindow]] = {
    "amazon": [
        # Best: Tuesday-Thursday, 9-11am EST (before peak shopping)
        TimeWindow(1, 9, 11, "US/Eastern", 0.95, "Peak indexing window"),
        TimeWindow(2, 9, 11, "US/Eastern", 0.95, "Peak indexing window"),
        TimeWindow(3, 9, 11, "US/Eastern", 0.90, "Good indexing day"),
        # Also good: Monday early
        TimeWindow(0, 8, 10, "US/Eastern", 0.80, "Week start boost"),
        # Avoid: Friday PM, weekends (slower reindexing)
        TimeWindow(4, 9, 11, "US/Eastern", 0.70, "End of week"),
    ],
    "ebay": [
        # Best: Sunday evening (most bidding activity)
        TimeWindow(6, 18, 21, "US/Pacific", 0.95, "Peak bidding hours"),
        TimeWindow(3, 18, 21, "US/Pacific", 0.85, "Thursday evening"),
        TimeWindow(0, 9, 12, "US/Pacific", 0.80, "Monday morning refresh"),
    ],
    "shopify": [
        # Independent stores - update before email campaigns
        TimeWindow(0, 7, 9, "US/Eastern", 0.90, "Before Mon email blast"),
        TimeWindow(1, 7, 9, "US/Eastern", 0.90, "Before Tue campaigns"),
        TimeWindow(3, 7, 9, "US/Eastern", 0.85, "Mid-week refresh"),
    ],
    "walmart": [
        # Similar to Amazon, weekday mornings
        TimeWindow(1, 8, 10, "US/Central", 0.90, "Tue morning optimal"),
        TimeWindow(2, 8, 10, "US/Central", 0.90, "Wed morning optimal"),
        TimeWindow(3, 8, 10, "US/Central", 0.85, "Thu morning good"),
    ],
    "aliexpress": [
        # Best: align with China working hours
        TimeWindow(0, 10, 12, "Asia/Shanghai", 0.90, "Monday China AM"),
        TimeWindow(1, 10, 12, "Asia/Shanghai", 0.90, "Tuesday China AM"),
        TimeWindow(2, 14, 16, "Asia/Shanghai", 0.85, "Wednesday PM"),
    ],
    "shopee": [
        TimeWindow(0, 10, 12, "Asia/Singapore", 0.90, "Monday SEA morning"),
        TimeWindow(3, 10, 12, "Asia/Singapore", 0.85, "Thursday morning"),
        TimeWindow(4, 14, 16, "Asia/Singapore", 0.80, "Friday before weekend"),
    ],
    "tiktok_shop": [
        # Align with content posting schedule
        TimeWindow(1, 17, 19, "US/Eastern", 0.90, "Tue evening content"),
        TimeWindow(3, 17, 19, "US/Eastern", 0.90, "Thu evening content"),
        TimeWindow(5, 10, 12, "US/Eastern", 0.85, "Sat morning browse"),
    ],
    "etsy": [
        TimeWindow(0, 9, 11, "US/Eastern", 0.90, "Monday morning"),
        TimeWindow(2, 9, 11, "US/Eastern", 0.85, "Wednesday morning"),
        TimeWindow(6, 8, 10, "US/Eastern", 0.80, "Sunday browse window"),
    ],
}

# ── Peak Season Calendar ────────────────────────────────────

PEAK_SEASONS = {
    "q4_prep": {
        "start_month": 9, "start_day": 15,
        "end_month": 10, "end_day": 15,
        "name": "Q4 Preparation",
        "boost": 1.5,
        "notes": "Optimize all listings before holiday season",
    },
    "black_friday": {
        "start_month": 11, "start_day": 15,
        "end_month": 11, "end_day": 30,
        "name": "Black Friday / Cyber Monday",
        "boost": 2.0,
        "notes": "Freeze non-critical changes; focus on pricing and promotions",
    },
    "holiday": {
        "start_month": 12, "start_day": 1,
        "end_month": 12, "end_day": 25,
        "name": "Holiday Season",
        "boost": 1.8,
        "notes": "Gift-focused keywords and descriptions",
    },
    "new_year": {
        "start_month": 1, "start_day": 1,
        "end_month": 1, "end_day": 15,
        "name": "New Year Sales",
        "boost": 1.3,
        "notes": "Clearance and resolution-themed content",
    },
    "valentines": {
        "start_month": 2, "start_day": 1,
        "end_month": 2, "end_day": 14,
        "name": "Valentine's Day",
        "boost": 1.2,
        "notes": "Gift and couples keywords",
    },
    "prime_day": {
        "start_month": 7, "start_day": 1,
        "end_month": 7, "end_day": 20,
        "name": "Amazon Prime Day",
        "boost": 1.7,
        "notes": "Amazon-specific event; optimize deal listings",
    },
    "singles_day": {
        "start_month": 11, "start_day": 1,
        "end_month": 11, "end_day": 11,
        "name": "Singles' Day (11.11)",
        "boost": 1.8,
        "notes": "Critical for AliExpress/Shopee",
    },
    "back_to_school": {
        "start_month": 7, "start_day": 15,
        "end_month": 9, "end_day": 5,
        "name": "Back to School",
        "boost": 1.3,
        "notes": "Education and supplies keywords",
    },
}

# ── Cooldown Rules ──────────────────────────────────────────

COOLDOWN_HOURS = {
    UpdateType.TITLE: 72,         # 3 days between title changes
    UpdateType.BULLETS: 48,       # 2 days between bullet updates
    UpdateType.DESCRIPTION: 48,
    UpdateType.IMAGES: 24,
    UpdateType.KEYWORDS: 72,
    UpdateType.PRICING: 6,        # Pricing can change more frequently
    UpdateType.FULL: 168,         # 7 days between full rewrites
    UpdateType.AB_TEST: 168,      # 7 days per test variant
}


def get_optimal_windows(
    platform: str,
    top_n: int = 3,
) -> list[TimeWindow]:
    """Get top optimal update windows for a platform."""
    windows = PLATFORM_WINDOWS.get(platform.lower(), [])
    if not windows:
        # Default windows for unknown platforms
        windows = [
            TimeWindow(1, 9, 11, "UTC", 0.80, "Default Tuesday morning"),
            TimeWindow(2, 9, 11, "UTC", 0.80, "Default Wednesday morning"),
        ]
    return sorted(windows, key=lambda w: w.score, reverse=True)[:top_n]


def get_active_seasons(date: Optional[datetime] = None) -> list[dict]:
    """Get currently active peak seasons."""
    if date is None:
        date = datetime.now()

    active = []
    month, day = date.month, date.day

    for key, season in PEAK_SEASONS.items():
        start = (season["start_month"], season["start_day"])
        end = (season["end_month"], season["end_day"])

        if start <= (month, day) <= end:
            active.append({**season, "key": key})

    return active


def check_cooldown(
    update_type: UpdateType,
    last_update: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> tuple[bool, float]:
    """Check if an update type is still in cooldown.

    Returns:
        (is_allowed, hours_remaining)
    """
    if last_update is None:
        return True, 0.0

    if now is None:
        now = datetime.now()

    cooldown = COOLDOWN_HOURS.get(update_type, 48)
    elapsed = (now - last_update).total_seconds() / 3600
    remaining = max(0, cooldown - elapsed)

    return remaining <= 0, remaining


def score_update_priority(
    listing: dict,
    performance: Optional[dict] = None,
) -> UpdatePriority:
    """Score how urgently a listing needs updating.

    Args:
        listing: Dict with listing metadata.
        performance: Optional performance metrics dict.
    """
    urgency = 0.0

    # Check listing age
    last_updated = listing.get("last_updated")
    if last_updated:
        if isinstance(last_updated, str):
            try:
                last_updated = datetime.fromisoformat(last_updated)
            except ValueError:
                last_updated = None

    if last_updated:
        days_since = (datetime.now() - last_updated).days
        if days_since > 90:
            urgency += 40
        elif days_since > 60:
            urgency += 25
        elif days_since > 30:
            urgency += 15
        elif days_since > 14:
            urgency += 5

    # Check performance metrics
    if performance:
        ctr = performance.get("ctr", 0)
        conversion = performance.get("conversion_rate", 0)
        sessions = performance.get("sessions", 0)

        # Low CTR = title/image issue
        if ctr < 0.5 and sessions > 100:
            urgency += 30
        elif ctr < 1.0 and sessions > 50:
            urgency += 15

        # Low conversion = listing content issue
        if conversion < 2.0 and sessions > 50:
            urgency += 25
        elif conversion < 5.0 and sessions > 50:
            urgency += 10

        # High traffic + low conversion = big opportunity
        if sessions > 500 and conversion < 3.0:
            urgency += 20

    # Check listing completeness
    if not listing.get("bullets"):
        urgency += 20
    if not listing.get("description"):
        urgency += 15
    if not listing.get("images") or listing.get("image_count", 0) < 3:
        urgency += 15
    if not listing.get("keywords"):
        urgency += 10

    # Suppression / policy violation
    if listing.get("suppressed") or listing.get("policy_violation"):
        return UpdatePriority.CRITICAL

    # Map urgency to priority
    if urgency >= 60:
        return UpdatePriority.HIGH
    elif urgency >= 30:
        return UpdatePriority.MEDIUM
    elif urgency >= 10:
        return UpdatePriority.LOW
    return UpdatePriority.NONE


def find_next_window(
    platform: str,
    after: Optional[datetime] = None,
    prefer_score: float = 0.7,
) -> Optional[ScheduledUpdate]:
    """Find the next optimal time window for a platform.

    Returns a ScheduledUpdate with the scheduled_at set to the
    next occurrence of the best available window.
    """
    if after is None:
        after = datetime.now()

    windows = get_optimal_windows(platform, top_n=5)
    if not windows:
        return None

    best = None
    best_dt = None

    for window in windows:
        if window.score < prefer_score:
            continue

        # Find next occurrence of this day/hour
        target_dow = window.day_of_week
        current_dow = after.weekday()

        days_ahead = target_dow - current_dow
        if days_ahead < 0:
            days_ahead += 7
        elif days_ahead == 0:
            # Same day — check if hour is still ahead
            if after.hour >= window.hour_end:
                days_ahead = 7

        target_date = after + timedelta(days=days_ahead)
        target_dt = target_date.replace(
            hour=window.hour_start, minute=0, second=0, microsecond=0
        )

        if best_dt is None or target_dt < best_dt:
            best_dt = target_dt
            best = window

    if best and best_dt:
        return ScheduledUpdate(
            listing_id="",
            platform=platform,
            update_type=UpdateType.FULL,
            priority=UpdatePriority.MEDIUM,
            scheduled_at=best_dt,
            window=best,
        )

    return None


def plan_batch_updates(
    listings: list[dict],
    platform: str,
    performance_data: Optional[dict[str, dict]] = None,
    max_per_day: int = 10,
    start_date: Optional[datetime] = None,
) -> UpdatePlan:
    """Plan a batch of listing updates across optimal windows.

    Args:
        listings: List of listing dicts with 'id', 'last_updated', etc.
        platform: Target platform.
        performance_data: Optional {listing_id: metrics} dict.
        max_per_day: Maximum updates per day.
        start_date: When to start scheduling.

    Returns:
        UpdatePlan with scheduled updates.
    """
    if start_date is None:
        start_date = datetime.now()

    if performance_data is None:
        performance_data = {}

    # Score and sort by priority
    scored = []
    for listing in listings:
        lid = listing.get("id", listing.get("listing_id", "unknown"))
        perf = performance_data.get(lid)
        priority = score_update_priority(listing, perf)
        scored.append((listing, priority, lid))

    # Sort: critical > high > medium > low > none
    priority_order = {
        UpdatePriority.CRITICAL: 0,
        UpdatePriority.HIGH: 1,
        UpdatePriority.MEDIUM: 2,
        UpdatePriority.LOW: 3,
        UpdatePriority.NONE: 4,
    }
    scored.sort(key=lambda x: priority_order.get(x[1], 99))

    # Get windows
    windows = get_optimal_windows(platform, top_n=5)

    # Schedule across days
    updates: list[ScheduledUpdate] = []
    warnings: list[str] = []
    current_date = start_date
    day_count = 0

    for listing, priority, lid in scored:
        if priority == UpdatePriority.NONE:
            continue

        # Find next available slot
        if day_count >= max_per_day:
            current_date += timedelta(days=1)
            day_count = 0

        # Pick a window
        window = windows[day_count % len(windows)] if windows else None
        hour = window.hour_start if window else 9

        sched_dt = current_date.replace(
            hour=hour, minute=day_count * 5, second=0, microsecond=0
        )

        updates.append(ScheduledUpdate(
            listing_id=lid,
            platform=platform,
            update_type=UpdateType.FULL,
            priority=priority,
            scheduled_at=sched_dt,
            window=window,
        ))

        day_count += 1

    # Check for peak season warnings
    active_seasons = get_active_seasons(start_date)
    for season in active_seasons:
        warnings.append(
            f"⚡ {season['name']}: {season['notes']}"
        )

    # Risk assessment
    critical_count = sum(1 for _, p, _ in scored if p == UpdatePriority.CRITICAL)
    if critical_count > 0:
        risk = "high"
    elif len(updates) > 20:
        risk = "medium"
    else:
        risk = "low"

    return UpdatePlan(
        updates=updates,
        total_count=len(updates),
        estimated_duration_min=len(updates) * 3.0,
        risk_level=risk,
        warnings=warnings,
    )
