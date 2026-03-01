"""Tests for hijack_detector module."""

import pytest
from app.hijack_detector import (
    HijackDetector,
    AlertSeverity,
    AlertType,
    SellerRecord,
    BuyBoxStatus,
    HijackAlert,
    CounterfeitRisk,
    ListingHealth,
)


@pytest.fixture
def detector():
    return HijackDetector(your_seller_id="my_store")


@pytest.fixture
def sample_sellers():
    return [
        {"seller_id": "my_store", "seller_name": "My Store", "price": 29.99, "is_fba": True, "rating": 4.8, "review_count": 500},
        {"seller_id": "auth_seller", "seller_name": "Auth Partner", "price": 31.99, "is_fba": True, "rating": 4.5, "review_count": 200},
        {"seller_id": "shady_seller", "seller_name": "CheapGoods", "price": 19.99, "is_fba": False, "rating": 2.5, "review_count": 3},
    ]


class TestInit:
    def test_default_init(self, detector):
        assert detector.your_seller_id == "my_store"
        assert len(detector.alerts) == 0

    def test_custom_seller_id(self):
        d = HijackDetector(your_seller_id="custom_id")
        assert d.your_seller_id == "custom_id"


class TestAuthorizedSellers:
    def test_set_authorized(self, detector):
        detector.set_authorized_sellers("B001", ["seller_a", "seller_b"])
        assert "seller_a" in detector.authorized_sellers["B001"]
        assert "my_store" in detector.authorized_sellers["B001"]  # auto-add

    def test_auto_includes_self(self, detector):
        detector.set_authorized_sellers("B001", ["other"])
        assert "my_store" in detector.authorized_sellers["B001"]


class TestMAPPrice:
    def test_set_map(self, detector):
        detector.set_map_price("B001", 25.00)
        assert detector.map_prices["B001"] == 25.00

    def test_invalid_map_raises(self, detector):
        with pytest.raises(ValueError):
            detector.set_map_price("B001", 0)

    def test_negative_map_raises(self, detector):
        with pytest.raises(ValueError):
            detector.set_map_price("B001", -10)


class TestCheckSellers:
    def test_detect_unauthorized(self, detector, sample_sellers):
        detector.set_authorized_sellers("B001", ["my_store", "auth_seller"])
        alerts = detector.check_sellers("B001", sample_sellers)
        unauth = [a for a in alerts if a.alert_type == "unauthorized_seller"]
        assert len(unauth) == 1
        assert unauth[0].seller == "shady_seller"

    def test_no_alerts_all_authorized(self, detector, sample_sellers):
        detector.set_authorized_sellers(
            "B001", ["my_store", "auth_seller", "shady_seller"]
        )
        alerts = detector.check_sellers("B001", sample_sellers)
        unauth = [a for a in alerts if a.alert_type == "unauthorized_seller"]
        assert len(unauth) == 0

    def test_no_whitelist_no_unauthorized_alerts(self, detector, sample_sellers):
        alerts = detector.check_sellers("B001", sample_sellers)
        unauth = [a for a in alerts if a.alert_type == "unauthorized_seller"]
        assert len(unauth) == 0

    def test_map_violation(self, detector):
        detector.set_map_price("B001", 25.00)
        sellers = [
            {"seller_id": "cheap", "seller_name": "Cheap", "price": 18.00},
        ]
        alerts = detector.check_sellers("B001", sellers)
        map_alerts = [a for a in alerts if a.alert_type == "map_violation"]
        assert len(map_alerts) == 1
        assert map_alerts[0].severity in ["medium", "high", "critical"]

    def test_seller_surge(self, detector):
        # First check: 2 sellers
        detector.check_sellers("B001", [
            {"seller_id": "a", "seller_name": "A", "price": 20},
            {"seller_id": "b", "seller_name": "B", "price": 21},
        ])
        # Second check: 5 sellers (>1.5x)
        alerts = detector.check_sellers("B001", [
            {"seller_id": "a", "seller_name": "A", "price": 20},
            {"seller_id": "b", "seller_name": "B", "price": 21},
            {"seller_id": "c", "seller_name": "C", "price": 22},
            {"seller_id": "d", "seller_name": "D", "price": 23},
            {"seller_id": "e", "seller_name": "E", "price": 24},
        ])
        surge = [a for a in alerts if a.alert_type == "seller_surge"]
        assert len(surge) == 1

    def test_stores_seller_history(self, detector, sample_sellers):
        detector.check_sellers("B001", sample_sellers)
        assert "B001" in detector.seller_history
        assert len(detector.seller_history["B001"]) == 3


class TestBuyBox:
    def test_you_own_buybox(self, detector):
        status = detector.check_buybox("B001", "my_store", 29.99, 29.99)
        assert status.you_own_buybox is True
        assert status.win_rate_pct == 100.0

    def test_competitor_owns_buybox(self, detector):
        status = detector.check_buybox("B001", "other_seller", 27.99, 29.99)
        assert status.you_own_buybox is False

    def test_buybox_loss_alert(self, detector):
        # First: you own it
        detector.check_buybox("B001", "my_store", 29.99, 29.99)
        # Second: you lose it
        detector.check_buybox("B001", "competitor", 27.99, 29.99)
        loss_alerts = [a for a in detector.alerts if a.alert_type == "buybox_lost"]
        assert len(loss_alerts) == 1

    def test_win_rate_tracking(self, detector):
        detector.check_buybox("B001", "my_store", 29.99, 29.99)
        detector.check_buybox("B001", "other", 27.99, 29.99)
        detector.check_buybox("B001", "my_store", 29.99, 29.99)
        status = detector.check_buybox("B001", "my_store", 29.99, 29.99)
        assert status.win_rate_pct == 75.0  # 3/4
        assert status.total_checks == 4
        assert status.your_wins == 3

    def test_to_dict(self, detector):
        status = detector.check_buybox("B001", "my_store", 29.99, 29.99)
        d = status.to_dict()
        assert "asin" in d
        assert "you_own_buybox" in d


class TestCounterfeitRisk:
    def test_low_risk_seller(self, detector):
        seller = {
            "seller_id": "good",
            "seller_name": "Good Seller",
            "price": 30.00,
            "rating": 4.8,
            "review_count": 500,
            "account_age_days": 365,
            "is_fba": True,
        }
        risk = detector.assess_counterfeit_risk("B001", seller, avg_price=29.00)
        assert risk.risk_level == "low"
        assert risk.risk_score < 25

    def test_high_risk_seller(self, detector):
        seller = {
            "seller_id": "shady",
            "seller_name": "Shady Co",
            "price": 15.00,
            "rating": 2.0,
            "review_count": 2,
            "account_age_days": 10,
            "is_fba": False,
        }
        risk = detector.assess_counterfeit_risk("B001", seller, avg_price=30.00)
        assert risk.risk_score >= 50
        assert risk.risk_level in ["high", "critical"]
        assert len(risk.factors) >= 3

    def test_price_below_avg_flag(self, detector):
        seller = {
            "seller_id": "x",
            "seller_name": "X",
            "price": 10.00,
            "rating": 4.0,
            "review_count": 100,
            "is_fba": True,
        }
        risk = detector.assess_counterfeit_risk("B001", seller, avg_price=30.00)
        assert risk.price_vs_avg < -30
        assert any("below average" in f.lower() for f in risk.factors)

    def test_generates_alert_for_high_risk(self, detector):
        seller = {
            "seller_id": "bad",
            "seller_name": "Bad",
            "price": 10.00,
            "rating": 1.5,
            "review_count": 0,
            "account_age_days": 5,
            "is_fba": False,
        }
        detector.assess_counterfeit_risk("B001", seller, avg_price=30.00)
        cf_alerts = [a for a in detector.alerts if a.alert_type == "counterfeit_risk"]
        assert len(cf_alerts) >= 1

    def test_unauthorized_factor(self, detector):
        detector.set_authorized_sellers("B001", ["good_seller"])
        seller = {
            "seller_id": "unauth",
            "seller_name": "Unauth",
            "price": 28.00,
            "rating": 3.5,
            "review_count": 30,
            "is_fba": True,
        }
        risk = detector.assess_counterfeit_risk("B001", seller, avg_price=30.00)
        assert any("authorized" in f.lower() for f in risk.factors)


class TestPriceUndercut:
    def test_detect_undercut(self, detector):
        competitors = [
            {"seller_id": "c1", "seller_name": "Comp1", "price": 20.00},
            {"seller_id": "c2", "seller_name": "Comp2", "price": 28.00},
        ]
        alerts = detector.detect_price_undercut("B001", 30.00, competitors)
        assert len(alerts) == 1  # only c1 is >15% below
        assert alerts[0].seller == "c1"

    def test_no_undercut(self, detector):
        competitors = [
            {"seller_id": "c1", "seller_name": "Comp1", "price": 28.00},
        ]
        alerts = detector.detect_price_undercut("B001", 30.00, competitors)
        assert len(alerts) == 0

    def test_custom_threshold(self, detector):
        competitors = [
            {"seller_id": "c1", "seller_name": "Comp1", "price": 27.00},
        ]
        alerts = detector.detect_price_undercut("B001", 30.00, competitors, threshold_pct=5.0)
        assert len(alerts) == 1

    def test_severity_levels(self, detector):
        competitors = [
            {"seller_id": "c1", "seller_name": "Extreme", "price": 10.00},  # >40% undercut
        ]
        alerts = detector.detect_price_undercut("B001", 30.00, competitors)
        assert alerts[0].severity == "critical"


class TestListingHealth:
    def test_healthy_listing(self, detector):
        detector.set_authorized_sellers("B001", ["my_store"])
        detector.check_sellers("B001", [
            {"seller_id": "my_store", "seller_name": "My Store", "price": 30},
        ])
        detector.check_buybox("B001", "my_store", 30.00, 30.00)
        health = detector.listing_health("B001")
        assert health.health_score >= 80
        assert health.risk_level == "low"

    def test_unhealthy_listing(self, detector):
        detector.set_authorized_sellers("B001", ["my_store"])
        sellers = [
            {"seller_id": "my_store", "seller_name": "Me", "price": 30},
        ] + [
            {"seller_id": f"unauth_{i}", "seller_name": f"U{i}", "price": 20+i}
            for i in range(6)
        ]
        detector.check_sellers("B001", sellers)
        # Lose buybox
        detector.check_buybox("B001", "my_store", 30, 30)
        detector.check_buybox("B001", "unauth_0", 20, 30)
        health = detector.listing_health("B001")
        assert health.unauthorized_sellers > 0
        assert health.health_score < 80

    def test_recommendations(self, detector):
        health = detector.listing_health("B999")
        assert any("whitelist" in r.lower() for r in health.recommendations)

    def test_to_dict(self, detector):
        health = detector.listing_health("B001")
        d = health.to_dict()
        assert "health_score" in d
        assert "recommendations" in d


class TestAlertManagement:
    def test_get_alerts_filtered(self, detector):
        detector.set_authorized_sellers("B001", ["my_store"])
        detector.check_sellers("B001", [
            {"seller_id": "bad", "seller_name": "Bad", "price": 10},
        ])
        alerts = detector.get_alerts(asin="B001")
        assert len(alerts) >= 1

    def test_get_alerts_by_severity(self, detector):
        detector.set_authorized_sellers("B001", ["my_store"])
        detector.check_sellers("B001", [
            {"seller_id": "bad", "seller_name": "Bad", "price": 10},
        ])
        high = detector.get_alerts(severity="high")
        assert all(a.severity == "high" for a in high)

    def test_clear_alerts(self, detector):
        detector.set_authorized_sellers("B001", ["my_store"])
        detector.check_sellers("B001", [
            {"seller_id": "bad", "seller_name": "Bad", "price": 10},
        ])
        count = detector.clear_alerts()
        assert count >= 1
        assert len(detector.alerts) == 0

    def test_clear_alerts_by_asin(self, detector):
        detector.set_authorized_sellers("B001", ["my_store"])
        detector.set_authorized_sellers("B002", ["my_store"])
        detector.check_sellers("B001", [{"seller_id": "x", "seller_name": "X", "price": 10}])
        detector.check_sellers("B002", [{"seller_id": "y", "seller_name": "Y", "price": 10}])
        detector.clear_alerts(asin="B001")
        remaining = detector.get_alerts()
        assert all(a.asin != "B001" for a in remaining)

    def test_alert_limit(self, detector):
        detector.set_authorized_sellers("B001", ["my_store"])
        for i in range(10):
            detector.check_sellers("B001", [
                {"seller_id": f"s{i}", "seller_name": f"S{i}", "price": 10},
            ])
        limited = detector.get_alerts(limit=3)
        assert len(limited) <= 3


class TestEnums:
    def test_alert_severity(self):
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.LOW.value == "low"

    def test_alert_type(self):
        assert AlertType.BUYBOX_LOST.value == "buybox_lost"
        assert AlertType.COUNTERFEIT_RISK.value == "counterfeit_risk"
