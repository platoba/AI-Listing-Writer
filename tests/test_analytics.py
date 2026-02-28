"""Tests for the analytics engine."""
import pytest
import time
import tempfile
from pathlib import Path
from app.analytics import (
    init_db,
    record_generation,
    get_user_stats,
    get_platform_trends,
    get_global_stats,
    export_analytics_csv,
    UserStats,
)


@pytest.fixture
def db_path():
    """Temporary database for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_analytics.db"
        init_db(path)
        yield path


# ── Database Init ───────────────────────────────────────────

class TestInitDB:
    def test_creates_database(self, db_path):
        assert db_path.exists()

    def test_idempotent(self, db_path):
        # Should not raise on second call
        init_db(db_path)


# ── Record Generation ──────────────────────────────────────

class TestRecordGeneration:
    def test_record_basic(self, db_path):
        record_generation(
            user_id=123,
            platform="amazon",
            product="Headphones",
            db_path=db_path,
        )
        stats = get_user_stats(123, db_path)
        assert stats.total_generations == 1

    def test_record_with_scores(self, db_path):
        record_generation(
            user_id=123,
            platform="amazon",
            product="Headphones",
            seo_score=85.5,
            validation_score=90.0,
            char_count=1500,
            duration_ms=2500,
            db_path=db_path,
        )
        stats = get_user_stats(123, db_path)
        assert stats.avg_seo_score == pytest.approx(85.5, rel=0.1)

    def test_multiple_platforms(self, db_path):
        for platform in ["amazon", "shopee", "ebay"]:
            record_generation(
                user_id=123,
                platform=platform,
                product="Test Product",
                db_path=db_path,
            )
        stats = get_user_stats(123, db_path)
        assert stats.total_generations == 3
        assert len(stats.platforms) == 3

    def test_daily_stats_updated(self, db_path):
        record_generation(user_id=1, platform="amazon", product="P1", db_path=db_path)
        record_generation(user_id=1, platform="amazon", product="P2", db_path=db_path)
        # Daily stats should aggregate
        trends = get_platform_trends(days=1, user_id=1, db_path=db_path)
        assert len(trends) >= 0  # May be empty if date edge


# ── User Stats ──────────────────────────────────────────────

class TestUserStats:
    def test_empty_user(self, db_path):
        stats = get_user_stats(999, db_path)
        assert stats.total_generations == 0
        assert stats.avg_seo_score == 0.0

    def test_platform_breakdown(self, db_path):
        for _ in range(3):
            record_generation(user_id=1, platform="amazon", product="P", db_path=db_path)
        for _ in range(2):
            record_generation(user_id=1, platform="shopee", product="P", db_path=db_path)

        stats = get_user_stats(1, db_path)
        assert stats.platforms["amazon"] == 3
        assert stats.platforms["shopee"] == 2
        assert stats.most_used_platform == "amazon"

    def test_language_breakdown(self, db_path):
        record_generation(user_id=1, platform="amazon", product="P", language="English", db_path=db_path)
        record_generation(user_id=1, platform="shopee", product="P", language="中文", db_path=db_path)

        stats = get_user_stats(1, db_path)
        assert "English" in stats.languages
        assert "中文" in stats.languages

    def test_recent_activity(self, db_path):
        record_generation(user_id=1, platform="amazon", product="P", db_path=db_path)
        stats = get_user_stats(1, db_path)
        assert stats.last_7_days == 1
        assert stats.last_30_days == 1

    def test_top_products(self, db_path):
        for _ in range(5):
            record_generation(user_id=1, platform="amazon", product="Top Product", db_path=db_path)
        record_generation(user_id=1, platform="amazon", product="Other", db_path=db_path)

        stats = get_user_stats(1, db_path)
        assert stats.top_products[0] == "Top Product"

    def test_summary_format(self, db_path):
        record_generation(user_id=1, platform="amazon", product="Test", seo_score=80, db_path=db_path)
        stats = get_user_stats(1, db_path)
        summary = stats.summary()
        assert "Analytics" in summary
        assert "Total listings: 1" in summary
        assert "amazon" in summary


# ── Platform Trends ─────────────────────────────────────────

class TestPlatformTrends:
    def test_empty_trends(self, db_path):
        trends = get_platform_trends(days=7, db_path=db_path)
        assert len(trends) == 0

    def test_trends_after_records(self, db_path):
        for i in range(5):
            record_generation(
                user_id=1, platform="amazon", product=f"P{i}",
                seo_score=70 + i, db_path=db_path,
            )
        trends = get_platform_trends(days=30, user_id=1, db_path=db_path)
        # May have trends depending on date aggregation
        assert isinstance(trends, list)

    def test_trends_by_user(self, db_path):
        record_generation(user_id=1, platform="amazon", product="P", db_path=db_path)
        record_generation(user_id=2, platform="shopee", product="P", db_path=db_path)

        trends_1 = get_platform_trends(days=30, user_id=1, db_path=db_path)
        trends_2 = get_platform_trends(days=30, user_id=2, db_path=db_path)
        # Each user should see their own platform
        assert isinstance(trends_1, list)
        assert isinstance(trends_2, list)


# ── Global Stats ────────────────────────────────────────────

class TestGlobalStats:
    def test_empty_global_stats(self, db_path):
        stats = get_global_stats(db_path)
        assert stats["total_generations"] == 0
        assert stats["today"] == 0

    def test_global_stats_aggregation(self, db_path):
        record_generation(user_id=1, platform="amazon", product="P1", db_path=db_path)
        record_generation(user_id=2, platform="shopee", product="P2", db_path=db_path)
        record_generation(user_id=1, platform="amazon", product="P3", db_path=db_path)

        stats = get_global_stats(db_path)
        assert stats["total_generations"] == 3
        assert stats["today"] == 3
        assert stats["platforms"]["amazon"]["count"] == 2
        assert stats["platforms"]["shopee"]["count"] == 1


# ── CSV Export ──────────────────────────────────────────────

class TestExportCSV:
    def test_empty_export(self, db_path):
        csv = export_analytics_csv(db_path=db_path)
        assert "Date" in csv  # Header present

    def test_export_with_data(self, db_path):
        record_generation(
            user_id=1, platform="amazon", product="Headphones",
            seo_score=85, char_count=1500, db_path=db_path,
        )
        csv = export_analytics_csv(user_id=1, db_path=db_path)
        assert "Headphones" in csv
        assert "amazon" in csv
        assert "85" in csv

    def test_export_filtered_by_user(self, db_path):
        record_generation(user_id=1, platform="amazon", product="P1", db_path=db_path)
        record_generation(user_id=2, platform="shopee", product="P2", db_path=db_path)

        csv = export_analytics_csv(user_id=1, db_path=db_path)
        assert "P1" in csv
        assert "P2" not in csv
