"""Tests for listing_health module."""

import json
import sqlite3
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest

from app.listing_health import (
    AlertSeverity,
    AlertType,
    HealthAlert,
    HealthCheck,
    HealthDatabase,
    HealthGrade,
    ListingHealth,
    ListingHealthMonitor,
)


@pytest.fixture
def tmp_db(tmp_path):
    return HealthDatabase(str(tmp_path / "test_health.db"))


@pytest.fixture
def monitor(tmp_db):
    return ListingHealthMonitor(tmp_db)


@pytest.fixture
def good_listing():
    return {
        "id": "B001234",
        "title": "Premium Wireless Bluetooth Earbuds with Active Noise Cancellation - 40H Battery, IPX7 Waterproof",
        "description": "Experience crystal clear audio with our premium wireless earbuds. "
                      "Featuring advanced active noise cancellation technology, "
                      "40-hour battery life, and IPX7 waterproof rating. "
                      "Perfect for commuting, working out, or relaxing at home. "
                      "The ergonomic design ensures a comfortable fit for all-day wear.",
        "bullet_points": [
            "Active Noise Cancellation - Block out ambient noise",
            "40-Hour Battery Life - Extended playback on a single charge",
            "IPX7 Waterproof - Sweat and splash resistant",
            "Bluetooth 5.3 - Stable low-latency connection",
            "Ergonomic Design - Comfortable fit with 3 ear tip sizes",
        ],
        "price": 49.99,
        "compare_price": 79.99,
        "cost": 15.00,
        "keywords": ["wireless earbuds", "bluetooth earbuds", "noise cancelling"],
        "backend_keywords": "earbuds headphones wireless bluetooth ANC waterproof",
        "images": [
            {"url": "img1.jpg", "width": 2000, "height": 2000, "alt_text": "Front view"},
            {"url": "img2.jpg", "width": 2000, "height": 2000, "alt_text": "Side view"},
            {"url": "img3.jpg", "width": 2000, "height": 2000, "alt_text": "In-ear shot"},
            {"url": "img4.jpg", "width": 2000, "height": 2000, "alt_text": "Case"},
        ],
        "category": "Electronics",
        "brand": "AudioPro",
        "sku": "AP-WE-001",
    }


@pytest.fixture
def bad_listing():
    return {
        "id": "BAD001",
        "title": "earbuds",
        "description": "Good.",
        "price": 0,
        "images": [],
    }


@pytest.fixture
def compliance_listing():
    return {
        "id": "COMP001",
        "title": "THE BEST #1 Guaranteed Miracle Earbuds FREE Risk-Free",
        "description": "These are the best earbuds. Cheapest price guaranteed. FDA approved quality. Number one seller.",
        "price": 10,
        "bullet_points": ["Great", "Amazing", "Best"],
        "images": [{"url": "img.jpg"}],
        "keywords": ["earbuds"],
        "category": "Electronics",
        "brand": "TestBrand",
    }


class TestHealthDatabase:
    def test_init_tables(self, tmp_db):
        conn = sqlite3.connect(tmp_db.db_path)
        tables = {t[0] for t in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "health_snapshots" in tables
        assert "health_alerts" in tables
        assert "monitored_listings" in tables
        conn.close()

    def test_save_and_get_health(self, tmp_db):
        health = ListingHealth(
            listing_id="TEST1", platform="amazon", title="Test",
            overall_score=85.0, grade=HealthGrade.A,
            checked_at=datetime.utcnow().isoformat(),
        )
        row_id = tmp_db.save_health(health)
        assert row_id > 0
        latest = tmp_db.get_latest_health("TEST1")
        assert latest is not None
        assert latest["overall_score"] == 85.0

    def test_get_health_history(self, tmp_db):
        for i in range(5):
            health = ListingHealth(
                listing_id="H1", platform="amazon", title="Test",
                overall_score=80 + i, grade=HealthGrade.A,
                checked_at=f"2026-01-0{i+1}T00:00:00",
            )
            tmp_db.save_health(health)
        history = tmp_db.get_health_history("H1")
        assert len(history) == 5

    def test_save_and_get_alert(self, tmp_db):
        alert = HealthAlert(
            listing_id="A1", alert_type=AlertType.SCORE_DROP,
            severity=AlertSeverity.WARNING,
            message="Score dropped by 15 points",
        )
        row_id = tmp_db.save_alert(alert)
        assert row_id > 0
        alerts = tmp_db.get_active_alerts("A1")
        assert len(alerts) == 1

    def test_resolve_alert(self, tmp_db):
        alert = HealthAlert(
            listing_id="R1", alert_type=AlertType.SCORE_DROP,
            severity=AlertSeverity.WARNING, message="test",
        )
        aid = tmp_db.save_alert(alert)
        tmp_db.resolve_alert(aid)
        alerts = tmp_db.get_active_alerts("R1")
        assert len(alerts) == 0

    def test_get_alerts_by_severity(self, tmp_db):
        for sev in [AlertSeverity.CRITICAL, AlertSeverity.WARNING, AlertSeverity.INFO]:
            tmp_db.save_alert(HealthAlert(
                listing_id="S1", alert_type=AlertType.SCORE_DROP,
                severity=sev, message=f"{sev.value} alert",
            ))
        critical = tmp_db.get_active_alerts(severity="critical")
        assert len(critical) == 1

    def test_monitored_listings(self, tmp_db):
        tmp_db.add_monitored_listing("M1", "amazon", "Test Product")
        due = tmp_db.get_due_listings()
        assert len(due) >= 1
        tmp_db.mark_checked("M1")
        due2 = tmp_db.get_due_listings()
        assert len(due2) == 0

    def test_dashboard_stats(self, tmp_db):
        stats = tmp_db.get_dashboard_stats()
        assert stats["total_listings"] == 0
        assert stats["active_alerts"] == 0


class TestListingHealthMonitor:
    def test_check_good_listing(self, monitor, good_listing):
        health = monitor.check_listing(good_listing, "amazon")
        assert health.overall_score > 70
        assert health.grade in (HealthGrade.A_PLUS, HealthGrade.A, HealthGrade.B)

    def test_check_bad_listing(self, monitor, bad_listing):
        health = monitor.check_listing(bad_listing, "amazon")
        assert health.overall_score < 50
        assert health.grade in (HealthGrade.D, HealthGrade.F)

    def test_check_generates_alerts(self, monitor, bad_listing):
        health = monitor.check_listing(bad_listing, "amazon")
        assert len(health.alerts) > 0

    def test_check_title_missing(self, monitor):
        check = monitor._check_title({}, "amazon")
        assert check.score == 0
        assert any("Missing" in i for i in check.issues)

    def test_check_title_good(self, monitor, good_listing):
        check = monitor._check_title(good_listing, "amazon")
        assert check.score > 10

    def test_check_title_too_short(self, monitor):
        check = monitor._check_title({"title": "Short"}, "amazon")
        assert any("short" in i.lower() for i in check.issues)

    def test_check_title_too_long(self, monitor):
        long_title = "A" * 250
        check = monitor._check_title({"title": long_title}, "amazon")
        assert any("exceed" in i.lower() for i in check.issues)

    def test_check_title_all_caps(self, monitor):
        check = monitor._check_title({"title": "ALL CAPS TITLE HERE FOR TESTING"}, "amazon")
        assert any("ALL CAPS" in i for i in check.issues)

    def test_check_title_no_caps(self, monitor):
        check = monitor._check_title({"title": "all lowercase title for testing product"}, "amazon")
        assert any("capitalization" in i.lower() for i in check.issues)

    def test_check_title_keyword_stuffing(self, monitor):
        check = monitor._check_title(
            {"title": "earbuds earbuds earbuds earbuds best earbuds wireless earbuds"}, "amazon"
        )
        assert any("stuffing" in i.lower() for i in check.issues)

    def test_check_description_missing(self, monitor):
        check = monitor._check_description({}, "amazon")
        assert any("Missing" in i for i in check.issues)

    def test_check_description_good(self, monitor, good_listing):
        check = monitor._check_description(good_listing, "amazon")
        assert check.score > 10

    def test_check_description_short(self, monitor):
        check = monitor._check_description({"description": "Short desc."}, "amazon")
        assert any("short" in i.lower() for i in check.issues)

    def test_check_description_bullets_missing(self, monitor):
        check = monitor._check_description({"description": "x" * 200}, "amazon")
        assert any("bullet" in i.lower() for i in check.issues)

    def test_check_seo_no_keywords(self, monitor):
        check = monitor._check_seo({"title": "Test Product"}, "amazon")
        assert any("keyword" in i.lower() for i in check.issues)

    def test_check_seo_good(self, monitor, good_listing):
        check = monitor._check_seo(good_listing, "amazon")
        assert check.score > 5

    def test_check_seo_primary_kw_missing(self, monitor):
        data = {
            "title": "Some Product Title",
            "description": "Description with wireless earbuds",
            "keywords": ["bluetooth headphones"],
        }
        check = monitor._check_seo(data, "amazon")
        assert any("Primary keyword" in i for i in check.issues)

    def test_check_seo_backend_keywords(self, monitor):
        check = monitor._check_seo({"title": "t", "keywords": ["k"]}, "amazon")
        assert any("backend" in i.lower() for i in check.issues)

    def test_check_images_none(self, monitor):
        check = monitor._check_images({}, "amazon")
        assert check.score == 0

    def test_check_images_few(self, monitor):
        check = monitor._check_images({"images": [{"url": "a.jpg"}]}, "amazon")
        assert any("image" in i.lower() for i in check.issues)

    def test_check_images_good(self, monitor, good_listing):
        check = monitor._check_images(good_listing, "amazon")
        assert check.score > 10

    def test_check_images_low_res(self, monitor):
        check = monitor._check_images({
            "images": [{"url": "a.jpg", "width": 500, "height": 500}]
        }, "amazon")
        assert any("resolution" in i.lower() for i in check.issues)

    def test_check_pricing_none(self, monitor):
        check = monitor._check_pricing({}, "amazon")
        assert check.score == 0

    def test_check_pricing_good(self, monitor, good_listing):
        check = monitor._check_pricing(good_listing, "amazon")
        assert check.score > 5

    def test_check_pricing_unrealistic_discount(self, monitor):
        check = monitor._check_pricing({"price": 5, "compare_price": 100}, "amazon")
        assert any("discount" in i.lower() for i in check.issues)

    def test_check_pricing_negative_margin(self, monitor):
        check = monitor._check_pricing({"price": 10, "cost": 20}, "amazon")
        assert any("below cost" in i.lower() for i in check.issues)

    def test_check_pricing_low_margin(self, monitor):
        check = monitor._check_pricing({"price": 10, "cost": 9}, "amazon")
        assert any("margin" in i.lower() for i in check.issues)

    def test_check_pricing_low_price(self, monitor):
        check = monitor._check_pricing({"price": 0.5}, "amazon")
        assert any("low price" in i.lower() for i in check.issues)

    def test_check_compliance_clean(self, monitor, good_listing):
        check = monitor._check_compliance(good_listing, "amazon")
        assert len(check.issues) == 0

    def test_check_compliance_prohibited(self, monitor, compliance_listing):
        check = monitor._check_compliance(compliance_listing, "amazon")
        assert len(check.issues) > 0

    def test_check_compliance_no_category(self, monitor):
        check = monitor._check_compliance({"title": "t", "description": "d"}, "amazon")
        assert any("category" in i.lower() for i in check.issues)

    def test_check_compliance_no_brand(self, monitor):
        check = monitor._check_compliance(
            {"title": "t", "description": "d", "category": "Electronics"}, "amazon"
        )
        assert any("brand" in i.lower() for i in check.issues)

    def test_check_content_quality_placeholder(self, monitor):
        check = monitor._check_content_quality(
            {"description": "Lorem ipsum dolor sit amet"}, "amazon"
        )
        assert any("Placeholder" in i for i in check.issues)

    def test_check_completeness_all_fields(self, monitor, good_listing):
        check = monitor._check_completeness(good_listing, "amazon")
        assert check.score > 3

    def test_check_completeness_missing(self, monitor):
        check = monitor._check_completeness({}, "amazon")
        assert len(check.issues) > 0

    def test_grade_a_plus(self, monitor):
        assert monitor._score_to_grade(96) == HealthGrade.A_PLUS

    def test_grade_a(self, monitor):
        assert monitor._score_to_grade(88) == HealthGrade.A

    def test_grade_b(self, monitor):
        assert monitor._score_to_grade(75) == HealthGrade.B

    def test_grade_c(self, monitor):
        assert monitor._score_to_grade(60) == HealthGrade.C

    def test_grade_d(self, monitor):
        assert monitor._score_to_grade(45) == HealthGrade.D

    def test_grade_f(self, monitor):
        assert monitor._score_to_grade(30) == HealthGrade.F

    def test_score_drop_alert(self, monitor, good_listing):
        # First check
        monitor.check_listing(good_listing, "amazon")
        # Second check with worse listing
        bad = dict(good_listing)
        bad["title"] = "bad"
        bad["description"] = ""
        bad["images"] = []
        bad["bullet_points"] = []
        health2 = monitor.check_listing(bad, "amazon")
        drop_alerts = [a for a in health2.alerts if a.get("alert_type") == "score_drop"]
        assert len(drop_alerts) > 0

    def test_batch_check(self, monitor, good_listing, bad_listing):
        results = monitor.batch_check([good_listing, bad_listing], "amazon")
        assert len(results) == 2
        assert results[0].overall_score <= results[1].overall_score  # sorted ascending

    def test_format_health_report(self, monitor, good_listing):
        health = monitor.check_listing(good_listing, "amazon")
        text = monitor.format_health_report(health)
        assert "Health" in text
        assert health.grade.value in text

    def test_format_batch_summary(self, monitor, good_listing, bad_listing):
        results = monitor.batch_check([good_listing, bad_listing])
        text = monitor.format_batch_summary(results)
        assert "Batch" in text
        assert "2" in text

    def test_format_batch_empty(self, monitor):
        text = monitor.format_batch_summary([])
        assert "No listings" in text

    def test_platform_limits(self, monitor):
        assert "amazon" in monitor.PLATFORM_LIMITS
        assert "shopee" in monitor.PLATFORM_LIMITS
        assert monitor.PLATFORM_LIMITS["amazon"]["title_max"] == 200
        assert monitor.PLATFORM_LIMITS["shopee"]["title_max"] == 120

    def test_shopee_description(self, monitor):
        """Shopee doesn't use bullet points."""
        check = monitor._check_description(
            {"description": "A" * 200}, "shopee"
        )
        # Should not complain about missing bullets
        assert not any("bullet" in i.lower() for i in check.issues)

    def test_content_quality_shopee_emoji(self, monitor):
        check = monitor._check_content_quality(
            {"description": "Great product for daily use"}, "shopee"
        )
        assert any("emoji" in s.lower() for s in check.suggestions)

    def test_check_images_alt_text_missing(self, monitor):
        check = monitor._check_images({
            "images": [
                {"url": "a.jpg", "width": 2000, "height": 2000},
                {"url": "b.jpg", "width": 2000, "height": 2000},
                {"url": "c.jpg", "width": 2000, "height": 2000},
            ]
        }, "amazon")
        assert any("alt text" in i.lower() for i in check.issues)

    def test_pricing_sale_above_compare(self, monitor):
        check = monitor._check_pricing({"price": 100, "compare_price": 80}, "amazon")
        assert any("higher" in i.lower() for i in check.issues)


class TestHealthEnums:
    def test_health_grade_values(self):
        assert HealthGrade.A_PLUS.value == "A+"
        assert HealthGrade.F.value == "F"

    def test_alert_severity(self):
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.WARNING.value == "warning"

    def test_alert_type(self):
        assert AlertType.SCORE_DROP.value == "score_drop"
        assert AlertType.COMPLIANCE_VIOLATION.value == "compliance_violation"


class TestHealthCheck:
    def test_creation(self):
        hc = HealthCheck("title", 15, 20, ["issue1"], ["suggestion1"])
        assert hc.category == "title"
        assert hc.score == 15
        assert hc.max_score == 20

    def test_defaults(self):
        hc = HealthCheck("test", 10, 10)
        assert hc.issues == []
        assert hc.suggestions == []
