"""Tests for Supply Chain Risk Analyzer."""

import pytest
import os
import tempfile
import sqlite3
from app.supply_chain_risk import (
    SupplyChainRiskAnalyzer, RiskFactor, SupplierProfile, LeadTimeEstimate,
    SupplyChainReport, RiskLevel, RiskCategory, OriginRegion,
    COUNTRY_RISK_PROFILES, SEASONAL_RISK_CALENDAR, CATEGORY_RISK_MODIFIERS,
    _score_to_level, _resolve_country, _detect_origin_from_listing,
    _detect_category,
)


# ── Fixtures ────────────────────────────────────────────

@pytest.fixture
def analyzer():
    return SupplyChainRiskAnalyzer()


@pytest.fixture
def db_analyzer(tmp_path):
    db = str(tmp_path / "risk.db")
    return SupplyChainRiskAnalyzer(db_path=db)


@pytest.fixture
def sample_suppliers():
    return [
        {"name": "Shenzhen Electronics Co.", "country": "CN", "share_pct": 60,
         "quality_score": 80, "reliability_score": 85, "backup_available": True,
         "certifications": ["ISO9001"]},
        {"name": "Vietnam Parts Ltd.", "country": "VN", "share_pct": 40,
         "quality_score": 72, "reliability_score": 70, "backup_available": False},
    ]


# ══════════════════════════════════════════════════════════
# Helper Tests
# ══════════════════════════════════════════════════════════

class TestScoreToLevel:
    def test_critical(self):
        assert _score_to_level(85) == "critical"
        assert _score_to_level(100) == "critical"

    def test_high(self):
        assert _score_to_level(60) == "high"
        assert _score_to_level(79) == "high"

    def test_medium(self):
        assert _score_to_level(40) == "medium"
        assert _score_to_level(59) == "medium"

    def test_low(self):
        assert _score_to_level(20) == "low"
        assert _score_to_level(39) == "low"

    def test_minimal(self):
        assert _score_to_level(0) == "minimal"
        assert _score_to_level(19) == "minimal"

    def test_boundary_80(self):
        assert _score_to_level(80) == "critical"


class TestResolveCountry:
    def test_iso_code(self):
        assert _resolve_country("CN") == "CN"
        assert _resolve_country("US") == "US"
        assert _resolve_country("JP") == "JP"

    def test_alias_english(self):
        assert _resolve_country("china") == "CN"
        assert _resolve_country("japan") == "JP"
        assert _resolve_country("united states") == "US"

    def test_alias_chinese(self):
        assert _resolve_country("中国") == "CN"
        assert _resolve_country("日本") == "JP"
        assert _resolve_country("越南") == "VN"

    def test_case_insensitive(self):
        assert _resolve_country("China") == "CN"
        assert _resolve_country("JAPAN") is None  # Aliases are lowercase