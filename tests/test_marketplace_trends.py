"""Tests for marketplace_trends module."""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.marketplace_trends import (
    CrossPlatformTrend,
    NicheOpportunity,
    NicheStatus,
    TrendAnalysis,
    TrendAnalyzer,
    TrendDataPoint,
    TrendDirection,
    TrendsDatabase,
)


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test_trends.db")
    return TrendsDatabase(db_path)


@pytest.fixture
def analyzer(tmp_db):
    return TrendAnalyzer(tmp_db)


@pytest.fixture
def sample_points():
    base = datetime.utcnow() - timedelta(days=30)
    points = []
    for i in range(30):
        dt = base + timedelta(days=i)
        points.append(TrendDataPoint(
            keyword="wireless earbuds",
            platform="amazon",
            volume=1000 + i * 50,  # Rising trend
            competition=0.4,
            timestamp=dt.isoformat(),
            category="Electronics",
            region="US",
        ))
    return points


@pytest.fixture
def declining_points():
    base = datetime.utcnow() - timedelta(days=30)
    points = []
    for i in range(30):
        dt = base + timedelta(days=i)
        points.append(TrendDataPoint(
            keyword="fidget spinner",
            platform="amazon",
            volume=5000 - i * 100,
            competition=0.8,
            timestamp=dt.isoformat(),
            category="Toys",
        ))
    return points


class TestTrendDataPoint:
    def test_creation(self):
        p = TrendDataPoint(
            keyword="test", platform="amazon", volume=100,
            competition=0.5, timestamp="2026-01-01T00:00:00",
        )
        assert p.keyword == "test"
        assert p.volume == 100
        assert p.region == "global"

    def test_defaults(self):
        p = TrendDataPoint(
            keyword="k", platform="p", volume=0,
            competition=0, timestamp="t",
        )
        assert p.category == ""
        assert p.source == "manual"


class TestTrendsDatabase:
    def test_init_creates_tables(self, tmp_db):
        conn = sqlite3.connect(tmp_db.db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {t[0] for t in tables}
        assert "trend_data" in names
        assert "niche_snapshots" in names
        assert "keyword_relations" in names
        conn.close()

    def test_add_data_point(self, tmp_db):
        p = TrendDataPoint("test kw", "amazon", 500, 0.3, "2026-01-01")
        row_id = tmp_db.add_data_point(p)
        assert row_id > 0

    def test_add_normalizes_keyword(self, tmp_db):
        p = TrendDataPoint("  Test KW  ", "Amazon", 500, 0.3, "2026-01-01")
        tmp_db.add_data_point(p)
        history = tmp_db.get_keyword_history("test kw", "amazon", days=365)
        assert len(history) == 1

    def test_add_bulk_data(self, tmp_db, sample_points):
        count = tmp_db.add_bulk_data(sample_points)
        assert count == 30

    def test_get_keyword_history(self, tmp_db, sample_points):
        tmp_db.add_bulk_data(sample_points)
        history = tmp_db.get_keyword_history("wireless earbuds", "amazon", days=60)
        assert len(history) == 30

    def test_get_keyword_history_no_platform(self, tmp_db, sample_points):
        tmp_db.add_bulk_data(sample_points)
        history = tmp_db.get_keyword_history("wireless earbuds", days=60)
        assert len(history) == 30

    def test_get_keyword_history_empty(self, tmp_db):
        history = tmp_db.get_keyword_history("nonexistent")
        assert history == []

    def test_get_top_keywords(self, tmp_db, sample_points):
        tmp_db.add_bulk_data(sample_points)
        top = tmp_db.get_top_keywords(platform="amazon", limit=5, days=60)
        assert len(top) >= 1
        assert top[0]["keyword"] == "wireless earbuds"

    def test_get_top_keywords_no_platform(self, tmp_db, sample_points):
        tmp_db.add_bulk_data(sample_points)
        top = tmp_db.get_top_keywords(limit=5, days=60)
        assert len(top) >= 1

    def test_add_keyword_relation(self, tmp_db):
        tmp_db.add_keyword_relation("earbuds", "headphones", 0.8, "amazon")
        rels = tmp_db.get_related_keywords("earbuds")
        assert len(rels) == 1
        assert rels[0]["related_keyword"] == "headphones"

    def test_keyword_relation_upsert(self, tmp_db):
        tmp_db.add_keyword_relation("a", "b", 0.5)
        tmp_db.add_keyword_relation("a", "b", 0.9)
        rels = tmp_db.get_related_keywords("a")
        assert len(rels) == 1
        assert rels[0]["strength"] == 0.9

    def test_save_niche_snapshot(self, tmp_db):
        niche = NicheOpportunity(
            niche="Smart Home",
            status=NicheStatus.GROWING,
            score=75,
            platforms=["amazon", "shopee"],
            top_keywords=["smart plug", "smart bulb"],
        )
        tmp_db.save_niche_snapshot(niche, datetime.utcnow().isoformat())

    def test_get_stats_empty(self, tmp_db):
        stats = tmp_db.get_stats()
        assert stats["total_data_points"] == 0
        assert stats["unique_keywords"] == 0

    def test_get_stats_with_data(self, tmp_db, sample_points):
        tmp_db.add_bulk_data(sample_points)
        tmp_db.add_keyword_relation("a", "b", 0.5)
        stats = tmp_db.get_stats()
        assert stats["total_data_points"] == 30
        assert stats["unique_keywords"] == 1
        assert stats["keyword_relations"] == 1


class TestTrendAnalyzer:
    def test_analyze_new_keyword(self, analyzer):
        result = analyzer.analyze_keyword("brand_new_keyword")
        assert result.direction == TrendDirection.NEW
        assert result.data_points == 0
        assert result.opportunity_score == 0

    def test_analyze_rising_keyword(self, analyzer, sample_points):
        analyzer.db.add_bulk_data(sample_points)
        result = analyzer.analyze_keyword("wireless earbuds", "amazon")
        assert result.direction in (TrendDirection.RISING, TrendDirection.BREAKOUT)
        assert result.velocity > 0
        assert result.current_volume > 0
        assert result.data_points == 30

    def test_analyze_declining_keyword(self, analyzer, declining_points):
        analyzer.db.add_bulk_data(declining_points)
        result = analyzer.analyze_keyword("fidget spinner", "amazon")
        assert result.direction == TrendDirection.DECLINING
        assert result.velocity < 0

    def test_velocity_calculation(self, analyzer):
        assert analyzer._calculate_velocity([]) == 0.0
        assert analyzer._calculate_velocity([100]) == 0.0
        vel = analyzer._calculate_velocity([100, 100, 200, 200, 300])
        assert vel > 0

    def test_velocity_flat(self, analyzer):
        vel = analyzer._calculate_velocity([100, 100, 100, 100, 100])
        assert abs(vel) < 0.01

    def test_velocity_zero_start(self, analyzer):
        vel = analyzer._calculate_velocity([0, 0, 100, 200])
        assert vel == 1.0

    def test_direction_new(self, analyzer):
        d = analyzer._determine_direction(0, [100])
        assert d == TrendDirection.NEW

    def test_direction_breakout(self, analyzer):
        d = analyzer._determine_direction(0.6, [100, 200, 300])
        assert d == TrendDirection.BREAKOUT

    def test_direction_rising(self, analyzer):
        d = analyzer._determine_direction(0.2, [100, 120, 140])
        assert d == TrendDirection.RISING

    def test_direction_declining(self, analyzer):
        d = analyzer._determine_direction(-0.3, [300, 200, 100])
        assert d == TrendDirection.DECLINING

    def test_direction_stable(self, analyzer):
        d = analyzer._determine_direction(0.05, [100, 102, 98])
        assert d == TrendDirection.STABLE

    def test_seasonal_detection_insufficient_data(self, analyzer):
        result = analyzer._detect_seasonal_pattern([{"timestamp": "2026-01-01", "volume": 100}])
        assert result is None

    def test_seasonal_detection_no_pattern(self, analyzer):
        history = []
        for m in range(1, 13):
            history.append({"timestamp": f"2025-{m:02d}-15T00:00:00", "volume": 1000})
        result = analyzer._detect_seasonal_pattern(history)
        assert result is None

    def test_seasonal_detection_q4(self, analyzer):
        history = []
        for m in range(1, 13):
            vol = 5000 if m >= 10 else 1000
            history.append({"timestamp": f"2025-{m:02d}-15T00:00:00", "volume": vol})
        result = analyzer._detect_seasonal_pattern(history)
        assert result is not None
        assert "Holiday" in result or "Q4" in result

    def test_opportunity_score_range(self, analyzer):
        score = analyzer._calculate_opportunity_score(1000, 800, 0.5, 0.2, TrendDirection.RISING)
        assert 0 <= score <= 100

    def test_opportunity_high_vol_low_comp(self, analyzer):
        score = analyzer._calculate_opportunity_score(5000, 3000, 0.1, 0.3, TrendDirection.RISING)
        assert score > 60

    def test_opportunity_declining(self, analyzer):
        score = analyzer._calculate_opportunity_score(100, 500, 0.8, -0.5, TrendDirection.DECLINING)
        assert score < 50

    def test_discover_niches_empty(self, analyzer):
        niches = analyzer.discover_niches()
        assert niches == []

    def test_discover_niches_with_data(self, analyzer):
        base = datetime.utcnow() - timedelta(days=10)
        for i, kw in enumerate(["smart plug", "smart bulb", "smart switch", "smart sensor"]):
            for d in range(10):
                dt = base + timedelta(days=d)
                analyzer.db.add_data_point(TrendDataPoint(
                    keyword=kw, platform="amazon",
                    volume=500 + d * 20, competition=0.3,
                    timestamp=dt.isoformat(), category="Smart Home",
                ))
        niches = analyzer.discover_niches(min_keywords=3)
        assert len(niches) >= 1
        assert niches[0].niche == "Smart Home"

    def test_niche_classification_emerging(self, analyzer):
        status = analyzer._classify_niche(0.2, 0.4, 5)
        assert status == NicheStatus.EMERGING

    def test_niche_classification_saturated(self, analyzer):
        status = analyzer._classify_niche(0.8, 0.03, 10)
        assert status == NicheStatus.SATURATED

    def test_niche_classification_declining(self, analyzer):
        status = analyzer._classify_niche(0.5, -0.2, 5)
        assert status == NicheStatus.DECLINING

    def test_niche_classification_growing(self, analyzer):
        status = analyzer._classify_niche(0.4, 0.2, 5)
        assert status == NicheStatus.GROWING

    def test_niche_classification_mature(self, analyzer):
        status = analyzer._classify_niche(0.5, 0.06, 5)
        assert status == NicheStatus.MATURE

    def test_niche_score_range(self, analyzer):
        score = analyzer._score_niche(1000, 0.5, 0.1, 5, NicheStatus.GROWING)
        assert 0 <= score <= 100

    def test_niche_recommendation_emerging(self, analyzer):
        rec = analyzer._niche_recommendation(NicheStatus.EMERGING, 80, 0.2)
        assert "🔥" in rec

    def test_niche_recommendation_saturated(self, analyzer):
        rec = analyzer._niche_recommendation(NicheStatus.SATURATED, 30, 0.9)
        assert "⚠️" in rec

    def test_niche_recommendation_declining(self, analyzer):
        rec = analyzer._niche_recommendation(NicheStatus.DECLINING, 20, 0.5)
        assert "🚫" in rec

    def test_niche_recommendation_growing(self, analyzer):
        rec = analyzer._niche_recommendation(NicheStatus.GROWING, 60, 0.5)
        assert "✅" in rec

    def test_cross_platform_empty(self, analyzer):
        result = analyzer.cross_platform_analysis("nonexistent")
        assert result.keyword == "nonexistent"
        assert not result.platforms

    def test_cross_platform_multi(self, analyzer):
        base = datetime.utcnow() - timedelta(days=10)
        for platform in ["amazon", "ebay"]:
            for d in range(10):
                dt = base + timedelta(days=d)
                analyzer.db.add_data_point(TrendDataPoint(
                    keyword="phone case", platform=platform,
                    volume=1000 + d * 30, competition=0.4,
                    timestamp=dt.isoformat(),
                ))
        result = analyzer.cross_platform_analysis("phone case")
        assert len(result.platforms) == 2
        assert result.best_platform in ("amazon", "ebay")
        assert result.combined_score > 0

    def test_cross_platform_arbitrage(self, analyzer):
        base = datetime.utcnow() - timedelta(days=5)
        for d in range(5):
            dt = base + timedelta(days=d)
            analyzer.db.add_data_point(TrendDataPoint(
                keyword="gadget", platform="amazon",
                volume=1000, competition=0.9, timestamp=dt.isoformat(),
            ))
            analyzer.db.add_data_point(TrendDataPoint(
                keyword="gadget", platform="shopee",
                volume=1000, competition=0.2, timestamp=dt.isoformat(),
            ))
        result = analyzer.cross_platform_analysis("gadget")
        assert result.arbitrage_opportunity is True

    def test_generate_report_empty(self, analyzer):
        report = analyzer.generate_trend_report()
        assert report["total_analyzed"] == 0

    def test_generate_report_with_data(self, analyzer, sample_points):
        analyzer.db.add_bulk_data(sample_points)
        report = analyzer.generate_trend_report(days=60)
        assert report["total_analyzed"] >= 1
        assert "stats" in report
        assert "top_keywords" in report

    def test_format_report_text(self, analyzer, sample_points):
        analyzer.db.add_bulk_data(sample_points)
        report = analyzer.generate_trend_report(days=60)
        text = analyzer.format_report_text(report)
        assert "📊" in text
        assert "Marketplace Trends" in text

    def test_format_report_empty(self, analyzer):
        report = analyzer.generate_trend_report()
        text = analyzer.format_report_text(report)
        assert "📊" in text

    def test_supported_platforms(self, analyzer):
        assert "amazon" in analyzer.SUPPORTED_PLATFORMS
        assert "shopee" in analyzer.SUPPORTED_PLATFORMS
        assert len(analyzer.SUPPORTED_PLATFORMS) >= 6

    def test_seasonal_patterns(self, analyzer):
        assert "q4_holiday" in analyzer.SEASONAL_PATTERNS
        assert 12 in analyzer.SEASONAL_PATTERNS["q4_holiday"]["months"]


class TestTrendDirection:
    def test_values(self):
        assert TrendDirection.RISING.value == "rising"
        assert TrendDirection.BREAKOUT.value == "breakout"
        assert TrendDirection.DECLINING.value == "declining"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.NEW.value == "new"


class TestNicheStatus:
    def test_values(self):
        assert NicheStatus.EMERGING.value == "emerging"
        assert NicheStatus.SATURATED.value == "saturated"
        assert NicheStatus.DECLINING.value == "declining"


class TestTrendAnalysisDataclass:
    def test_creation(self):
        t = TrendAnalysis(
            keyword="test", platform="amazon", direction=TrendDirection.RISING,
            velocity=0.3, current_volume=1000, avg_volume=800,
            peak_volume=1200, competition=0.5, opportunity_score=70,
            first_seen="2026-01-01", data_points=30,
        )
        assert t.keyword == "test"
        assert t.related_keywords == []


class TestCrossPlatformTrend:
    def test_defaults(self):
        c = CrossPlatformTrend(keyword="test")
        assert c.platforms == {}
        assert c.global_direction == TrendDirection.STABLE
        assert c.arbitrage_opportunity is False


class TestNicheOpportunity:
    def test_defaults(self):
        n = NicheOpportunity(niche="test", status=NicheStatus.EMERGING, score=80)
        assert n.platforms == []
        assert n.estimated_demand == "unknown"
