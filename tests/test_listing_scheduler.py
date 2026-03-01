"""Tests for listing_scheduler module."""
from datetime import datetime, timedelta

import pytest

from app.listing_scheduler import (
    COOLDOWN_HOURS,
    PEAK_SEASONS,
    PLATFORM_WINDOWS,
    ScheduledUpdate,
    TimeWindow,
    UpdatePlan,
    UpdatePriority,
    UpdateType,
    check_cooldown,
    find_next_window,
    get_active_seasons,
    get_optimal_windows,
    plan_batch_updates,
    score_update_priority,
)


# ── TimeWindow ──────────────────────────────────────────────

class TestTimeWindow:
    def test_day_name(self):
        w = TimeWindow(0, 9, 11, "UTC", 0.9)
        assert w.day_name == "Monday"

    def test_day_name_sunday(self):
        w = TimeWindow(6, 9, 11, "UTC", 0.8)
        assert w.day_name == "Sunday"

    def test_score_range(self):
        w = TimeWindow(1, 9, 11, "UTC", 0.95)
        assert 0 <= w.score <= 1


# ── ScheduledUpdate ─────────────────────────────────────────

class TestScheduledUpdate:
    def test_not_overdue_when_future(self):
        u = ScheduledUpdate(
            listing_id="B001",
            platform="amazon",
            update_type=UpdateType.TITLE,
            priority=UpdatePriority.MEDIUM,
            scheduled_at=datetime.now() + timedelta(hours=1),
        )
        assert not u.is_overdue

    def test_overdue_when_past(self):
        u = ScheduledUpdate(
            listing_id="B001",
            platform="amazon",
            update_type=UpdateType.TITLE,
            priority=UpdatePriority.MEDIUM,
            scheduled_at=datetime.now() - timedelta(hours=1),
        )
        assert u.is_overdue

    def test_not_overdue_when_completed(self):
        u = ScheduledUpdate(
            listing_id="B001",
            platform="amazon",
            update_type=UpdateType.TITLE,
            priority=UpdatePriority.MEDIUM,
            scheduled_at=datetime.now() - timedelta(hours=1),
            status="completed",
        )
        assert not u.is_overdue


# ── Optimal Windows ─────────────────────────────────────────

class TestGetOptimalWindows:
    def test_amazon_windows(self):
        windows = get_optimal_windows("amazon", top_n=3)
        assert len(windows) == 3
        assert all(isinstance(w, TimeWindow) for w in windows)
        # Should be sorted by score descending
        for i in range(len(windows) - 1):
            assert windows[i].score >= windows[i + 1].score

    def test_ebay_windows(self):
        windows = get_optimal_windows("ebay", top_n=2)
        assert len(windows) == 2

    def test_unknown_platform_fallback(self):
        windows = get_optimal_windows("unknown_platform", top_n=2)
        assert len(windows) == 2
        assert all(w.timezone == "UTC" for w in windows)

    def test_all_platforms_have_windows(self):
        for platform in PLATFORM_WINDOWS:
            windows = get_optimal_windows(platform)
            assert len(windows) > 0

    def test_top_n_limit(self):
        windows = get_optimal_windows("amazon", top_n=1)
        assert len(windows) == 1

    def test_scores_between_0_and_1(self):
        for platform in PLATFORM_WINDOWS:
            for w in get_optimal_windows(platform, top_n=10):
                assert 0 <= w.score <= 1


# ── Peak Seasons ────────────────────────────────────────────

class TestGetActiveSeasons:
    def test_black_friday(self):
        date = datetime(2025, 11, 25)
        seasons = get_active_seasons(date)
        names = [s["name"] for s in seasons]
        assert "Black Friday / Cyber Monday" in names

    def test_holiday(self):
        date = datetime(2025, 12, 15)
        seasons = get_active_seasons(date)
        names = [s["name"] for s in seasons]
        assert "Holiday Season" in names

    def test_prime_day(self):
        date = datetime(2025, 7, 10)
        seasons = get_active_seasons(date)
        names = [s["name"] for s in seasons]
        assert "Amazon Prime Day" in names

    def test_no_season(self):
        # March 15 — typically no peak season
        date = datetime(2025, 3, 15)
        seasons = get_active_seasons(date)
        assert isinstance(seasons, list)

    def test_valentines(self):
        date = datetime(2025, 2, 10)
        seasons = get_active_seasons(date)
        names = [s["name"] for s in seasons]
        assert "Valentine's Day" in names

    def test_singles_day(self):
        date = datetime(2025, 11, 8)
        seasons = get_active_seasons(date)
        names = [s["name"] for s in seasons]
        assert "Singles' Day (11.11)" in names

    def test_season_has_boost(self):
        for _, season in PEAK_SEASONS.items():
            assert season["boost"] >= 1.0

    def test_default_uses_now(self):
        seasons = get_active_seasons()
        assert isinstance(seasons, list)


# ── Cooldown ────────────────────────────────────────────────

class TestCheckCooldown:
    def test_no_last_update(self):
        allowed, remaining = check_cooldown(UpdateType.TITLE, last_update=None)
        assert allowed is True
        assert remaining == 0.0

    def test_within_cooldown(self):
        now = datetime.now()
        last = now - timedelta(hours=1)
        allowed, remaining = check_cooldown(UpdateType.TITLE, last_update=last, now=now)
        assert allowed is False
        assert remaining > 0

    def test_past_cooldown(self):
        now = datetime.now()
        last = now - timedelta(hours=200)
        allowed, remaining = check_cooldown(UpdateType.TITLE, last_update=last, now=now)
        assert allowed is True
        assert remaining == 0.0

    def test_pricing_short_cooldown(self):
        now = datetime.now()
        last = now - timedelta(hours=7)
        allowed, _ = check_cooldown(UpdateType.PRICING, last_update=last, now=now)
        assert allowed is True

    def test_full_rewrite_long_cooldown(self):
        now = datetime.now()
        last = now - timedelta(hours=100)
        allowed, _ = check_cooldown(UpdateType.FULL, last_update=last, now=now)
        assert allowed is False  # 168h cooldown

    def test_all_types_have_cooldown(self):
        for ut in UpdateType:
            assert ut in COOLDOWN_HOURS


# ── Update Priority ─────────────────────────────────────────

class TestScoreUpdatePriority:
    def test_suppressed_listing(self):
        listing = {"suppressed": True}
        assert score_update_priority(listing) == UpdatePriority.CRITICAL

    def test_policy_violation(self):
        listing = {"policy_violation": True}
        assert score_update_priority(listing) == UpdatePriority.CRITICAL

    def test_old_listing_high_priority(self):
        listing = {"last_updated": (datetime.now() - timedelta(days=100)).isoformat()}
        priority = score_update_priority(listing)
        assert priority in (UpdatePriority.HIGH, UpdatePriority.MEDIUM)

    def test_recent_listing_low_priority(self):
        listing = {
            "last_updated": datetime.now().isoformat(),
            "bullets": True,
            "description": True,
            "images": True,
            "image_count": 5,
            "keywords": True,
        }
        priority = score_update_priority(listing)
        assert priority in (UpdatePriority.LOW, UpdatePriority.NONE)

    def test_low_ctr_with_traffic(self):
        listing = {"last_updated": datetime.now().isoformat()}
        perf = {"ctr": 0.3, "conversion_rate": 1.0, "sessions": 200}
        priority = score_update_priority(listing, perf)
        assert priority in (UpdatePriority.HIGH, UpdatePriority.MEDIUM)

    def test_high_traffic_low_conversion(self):
        listing = {"last_updated": datetime.now().isoformat()}
        perf = {"ctr": 2.0, "conversion_rate": 1.5, "sessions": 600}
        priority = score_update_priority(listing, perf)
        assert priority in (UpdatePriority.HIGH, UpdatePriority.MEDIUM)

    def test_missing_bullets(self):
        listing = {"last_updated": datetime.now().isoformat()}
        priority = score_update_priority(listing)
        assert priority != UpdatePriority.NONE

    def test_complete_listing_no_perf(self):
        listing = {
            "last_updated": datetime.now().isoformat(),
            "bullets": True,
            "description": True,
            "images": ["img1", "img2", "img3"],
            "image_count": 5,
            "keywords": ["k1", "k2"],
        }
        priority = score_update_priority(listing)
        assert priority in (UpdatePriority.LOW, UpdatePriority.NONE)


# ── Find Next Window ────────────────────────────────────────

class TestFindNextWindow:
    def test_amazon_next_window(self):
        result = find_next_window("amazon")
        assert result is not None
        assert result.platform == "amazon"
        assert result.scheduled_at > datetime.now()

    def test_ebay_next_window(self):
        result = find_next_window("ebay")
        assert result is not None

    def test_unknown_platform(self):
        result = find_next_window("unknown_platform")
        assert result is not None

    def test_after_param(self):
        after = datetime(2025, 6, 1, 12, 0)
        result = find_next_window("amazon", after=after)
        assert result is not None
        assert result.scheduled_at >= after

    def test_high_prefer_score_filter(self):
        result = find_next_window("amazon", prefer_score=0.99)
        # May return None if no window meets the threshold
        if result is not None:
            assert result.window.score >= 0.99


# ── Batch Planning ──────────────────────────────────────────

class TestPlanBatchUpdates:
    def test_basic_plan(self):
        listings = [
            {"id": "B001", "last_updated": (datetime.now() - timedelta(days=60)).isoformat()},
            {"id": "B002", "last_updated": (datetime.now() - timedelta(days=30)).isoformat()},
            {"id": "B003", "last_updated": datetime.now().isoformat(),
             "bullets": True, "description": True, "images": True,
             "image_count": 5, "keywords": True},
        ]
        plan = plan_batch_updates(listings, "amazon")
        assert isinstance(plan, UpdatePlan)
        assert plan.total_count >= 0
        assert plan.risk_level in ("low", "medium", "high")

    def test_empty_listings(self):
        plan = plan_batch_updates([], "amazon")
        assert plan.total_count == 0

    def test_with_performance_data(self):
        listings = [{"id": "B001", "last_updated": datetime.now().isoformat()}]
        perf = {"B001": {"ctr": 0.2, "conversion_rate": 0.5, "sessions": 500}}
        plan = plan_batch_updates(listings, "amazon", performance_data=perf)
        assert plan.total_count > 0

    def test_critical_listing_high_risk(self):
        listings = [
            {"id": "B001", "suppressed": True},
        ]
        plan = plan_batch_updates(listings, "amazon")
        assert plan.risk_level == "high"

    def test_max_per_day_limit(self):
        listings = [
            {"id": f"B{i:03d}", "last_updated": (datetime.now() - timedelta(days=90)).isoformat()}
            for i in range(20)
        ]
        plan = plan_batch_updates(listings, "amazon", max_per_day=5)
        # Updates should span multiple days
        if plan.total_count > 5:
            dates = set(u.scheduled_at.date() for u in plan.updates)
            assert len(dates) > 1

    def test_peak_season_warnings(self):
        # Schedule during Black Friday
        start = datetime(2025, 11, 20)
        listings = [{"id": "B001", "last_updated": "2025-08-01"}]
        plan = plan_batch_updates(listings, "amazon", start_date=start)
        # Should have warning about peak season
        assert any("Black Friday" in w for w in plan.warnings)

    def test_summary_method(self):
        listings = [
            {"id": "B001", "last_updated": (datetime.now() - timedelta(days=60)).isoformat()},
        ]
        plan = plan_batch_updates(listings, "amazon")
        summary = plan.summary()
        assert "Update Plan" in summary
        assert isinstance(summary, str)

    def test_priority_ordering(self):
        listings = [
            {"id": "B001", "last_updated": datetime.now().isoformat(),
             "bullets": True, "description": True, "images": True,
             "image_count": 5, "keywords": True},  # low priority
            {"id": "B002", "suppressed": True},  # critical
        ]
        plan = plan_batch_updates(listings, "amazon")
        if len(plan.updates) >= 2:
            assert plan.updates[0].priority.value in ("critical", "high")
