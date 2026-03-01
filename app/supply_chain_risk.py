"""Supply Chain Risk Analyzer — assess sourcing risk, supplier diversification,
lead time estimation, and disruption vulnerability from listing metadata.

Features:
- Multi-factor risk scoring (0-100)
- Origin country risk profiling (political, logistics, tariff)
- Supplier concentration analysis (single-source detection)
- Lead time estimation & buffer calculation
- Seasonal supply risk calendar
- Tariff & trade war impact assessment
- Alternative sourcing suggestions
- Risk mitigation playbook generation
- Historical disruption pattern detection
- Supply chain resilience scoring
"""

from __future__ import annotations

import re
import math
import sqlite3
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    CRITICAL = "critical"   # 80-100: immediate action needed
    HIGH = "high"           # 60-79: significant risk
    MEDIUM = "medium"       # 40-59: moderate risk
    LOW = "low"             # 20-39: manageable
    MINIMAL = "minimal"     # 0-19: well-protected


class RiskCategory(str, Enum):
    SOURCING = "sourcing"
    LOGISTICS = "logistics"
    TARIFF = "tariff"
    GEOPOLITICAL = "geopolitical"
    QUALITY = "quality"
    DEMAND_VOLATILITY = "demand_volatility"
    SUPPLIER_CONCENTRATION = "supplier_concentration"
    LEAD_TIME = "lead_time"
    INVENTORY = "inventory"
    COMPLIANCE = "compliance"


class OriginRegion(str, Enum):
    CHINA = "china"
    SOUTHEAST_ASIA = "southeast_asia"
    INDIA = "india"
    EUROPE = "europe"
    NORTH_AMERICA = "north_america"
    SOUTH_AMERICA = "south_america"
    AFRICA = "africa"
    MIDDLE_EAST = "middle_east"
    OCEANIA = "oceania"


# Country risk profiles: stability (0=unstable), logistics (0=poor), tariff (0=high tariffs)
COUNTRY_RISK_PROFILES: dict[str, dict] = {
    "CN": {"region": "china", "stability": 70, "logistics": 85, "tariff_risk": 75,
            "lead_days": 25, "aliases": ["china", "中国", "prc"]},
    "VN": {"region": "southeast_asia", "stability": 72, "logistics": 65, "tariff_risk": 35,
            "lead_days": 28, "aliases": ["vietnam", "越南"]},
    "IN": {"region": "india", "stability": 68, "logistics": 55, "tariff_risk": 45,
            "lead_days": 30, "aliases": ["india", "印度"]},
    "TH": {"region": "southeast_asia", "stability": 65, "logistics": 70, "tariff_risk": 30,
            "lead_days": 26, "aliases": ["thailand", "泰国"]},
    "MY": {"region": "southeast_asia", "stability": 75, "logistics": 72, "tariff_risk": 25,
            "lead_days": 24, "aliases": ["malaysia", "马来西亚"]},
    "ID": {"region": "southeast_asia", "stability": 62, "logistics": 55, "tariff_risk": 30,
            "lead_days": 30, "aliases": ["indonesia", "印尼"]},
    "BD": {"region": "india", "stability": 55, "logistics": 45, "tariff_risk": 20,
            "lead_days": 35, "aliases": ["bangladesh", "孟加拉"]},
    "KR": {"region": "china", "stability": 82, "logistics": 88, "tariff_risk": 20,
            "lead_days": 18, "aliases": ["south korea", "韩国"]},
    "JP": {"region": "china", "stability": 90, "logistics": 95, "tariff_risk": 15,
            "lead_days": 14, "aliases": ["japan", "日本"]},
    "TW": {"region": "china", "stability": 60, "logistics": 82, "tariff_risk": 30,
            "lead_days": 20, "aliases": ["taiwan", "台湾"]},
    "DE": {"region": "europe", "stability": 90, "logistics": 92, "tariff_risk": 10,
            "lead_days": 12, "aliases": ["germany", "德国"]},
    "US": {"region": "north_america", "stability": 85, "logistics": 90, "tariff_risk": 5,
            "lead_days": 7, "aliases": ["united states", "usa", "美国"]},
    "MX": {"region": "north_america", "stability": 62, "logistics": 65, "tariff_risk": 15,
            "lead_days": 10, "aliases": ["mexico", "墨西哥"]},
    "TR": {"region": "middle_east", "stability": 55, "logistics": 68, "tariff_risk": 40,
            "lead_days": 22, "aliases": ["turkey", "türkiye", "土耳其"]},
    "PK": {"region": "india", "stability": 45, "logistics": 40, "tariff_risk": 30,
            "lead_days": 35, "aliases": ["pakistan", "巴基斯坦"]},
    "PH": {"region": "southeast_asia", "stability": 60, "logistics": 55, "tariff_risk": 25,
            "lead_days": 28, "aliases": ["philippines", "菲律宾"]},
    "BR": {"region": "south_america", "stability": 58, "logistics": 55, "tariff_risk": 50,
            "lead_days": 35, "aliases": ["brazil", "巴西"]},
    "IT": {"region": "europe", "stability": 82, "logistics": 85, "tariff_risk": 10,
            "lead_days": 14, "aliases": ["italy", "意大利"]},
    "GB": {"region": "europe", "stability": 88, "logistics": 90, "tariff_risk": 12,
            "lead_days": 12, "aliases": ["uk", "united kingdom", "英国"]},
}

# Seasonal risk calendar: month → categories with elevated risk
SEASONAL_RISK_CALENDAR: dict[int, list[str]] = {
    1: ["logistics_congestion", "chinese_new_year_shutdown"],
    2: ["chinese_new_year_shutdown", "factory_restart_delays"],
    3: ["post_holiday_backlog"],
    6: ["monsoon_asia", "peak_shipping_demand_buildup"],
    7: ["monsoon_asia", "typhoon_season_start"],
    8: ["typhoon_season", "peak_manufacturing"],
    9: ["peak_manufacturing", "container_shortage_risk"],
    10: ["peak_shipping", "container_shortage", "golden_week_china"],
    11: ["peak_shipping", "black_friday_demand_surge"],
    12: ["year_end_congestion", "factory_shutdown_prep"],
}

# Product category risk modifiers
CATEGORY_RISK_MODIFIERS: dict[str, dict] = {
    "electronics": {"quality_risk": 1.3, "obsolescence": 1.5, "compliance": 1.4},
    "textiles": {"quality_risk": 1.0, "obsolescence": 0.8, "compliance": 1.1},
    "food": {"quality_risk": 1.5, "obsolescence": 2.0, "compliance": 1.8},
    "toys": {"quality_risk": 1.2, "obsolescence": 1.2, "compliance": 1.6},
    "cosmetics": {"quality_risk": 1.3, "obsolescence": 1.3, "compliance": 1.7},
    "furniture": {"quality_risk": 0.9, "obsolescence": 0.5, "compliance": 0.8},
    "automotive": {"quality_risk": 1.4, "obsolescence": 0.7, "compliance": 1.5},
    "health": {"quality_risk": 1.5, "obsolescence": 1.0, "compliance": 2.0},
    "general": {"quality_risk": 1.0, "obsolescence": 1.0, "compliance": 1.0},
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class RiskFactor:
    """Individual risk factor assessment."""
    category: str
    name: str
    score: float           # 0-100
    level: str = ""
    description: str = ""
    mitigation: str = ""
    impact: str = ""       # financial impact description

    def __post_init__(self):
        self.score = max(0.0, min(100.0, self.score))
        if not self.level:
            self.level = _score_to_level(self.score)


@dataclass
class SupplierProfile:
    """Supplier assessment."""
    name: str
    country: str
    share_pct: float           # % of total supply
    lead_days: int = 30
    quality_score: float = 70.0
    reliability_score: float = 70.0
    backup_available: bool = False
    certifications: list[str] = field(default_factory=list)

    def risk_score(self) -> float:
        base = 100 - (self.quality_score * 0.4 + self.reliability_score * 0.4)
        if self.share_pct > 80:
            base += 20
        elif self.share_pct > 50:
            base += 10
        if not self.backup_available:
            base += 10
        return max(0.0, min(100.0, base))


@dataclass
class LeadTimeEstimate:
    """Lead time breakdown."""
    manufacturing_days: int = 15
    shipping_days: int = 25
    customs_days: int = 5
    domestic_transit_days: int = 3
    buffer_days: int = 7

    @property
    def total_days(self) -> int:
        return (self.manufacturing_days + self.shipping_days +
                self.customs_days + self.domestic_transit_days + self.buffer_days)

    @property
    def minimum_days(self) -> int:
        return self.manufacturing_days + self.shipping_days + self.customs_days + self.domestic_transit_days

    def with_disruption(self, multiplier: float = 1.5) -> int:
        return int(self.total_days * multiplier)


@dataclass
class SupplyChainReport:
    """Complete supply chain risk report."""
    overall_score: float
    overall_level: str
    resilience_score: float
    risk_factors: list[RiskFactor] = field(default_factory=list)
    suppliers: list[SupplierProfile] = field(default_factory=list)
    lead_time: Optional[LeadTimeEstimate] = None
    seasonal_risks: list[dict] = field(default_factory=list)
    mitigations: list[dict] = field(default_factory=list)
    tariff_impact: dict = field(default_factory=dict)
    alternative_sources: list[dict] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.overall_level:
            self.overall_level = _score_to_level(self.overall_score)

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "overall_level": self.overall_level,
            "resilience_score": round(self.resilience_score, 1),
            "risk_factors": [asdict(r) for r in self.risk_factors],
            "suppliers": [asdict(s) for s in self.suppliers],
            "lead_time": asdict(self.lead_time) if self.lead_time else None,
            "seasonal_risks": self.seasonal_risks,
            "mitigations": self.mitigations,
            "tariff_impact": self.tariff_impact,
            "alternative_sources": self.alternative_sources,
            "timestamp": self.timestamp,
        }

    def summary(self) -> str:
        lines = [
            f"═══ Supply Chain Risk Report ═══",
            f"Overall Risk: {self.overall_score:.0f}/100 ({self.overall_level.upper()})",
            f"Resilience Score: {self.resilience_score:.0f}/100",
            f"Risk Factors: {len(self.risk_factors)}",
        ]
        if self.risk_factors:
            critical = [r for r in self.risk_factors if r.level == "critical"]
            high = [r for r in self.risk_factors if r.level == "high"]
            if critical:
                lines.append(f"  🔴 Critical: {len(critical)}")
            if high:
                lines.append(f"  🟠 High: {len(high)}")
        if self.lead_time:
            lines.append(f"Lead Time: {self.lead_time.total_days} days "
                        f"(min {self.lead_time.minimum_days}d)")
        if self.mitigations:
            lines.append(f"Mitigations: {len(self.mitigations)} recommended")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_to_level(score: float) -> str:
    if score >= 80:
        return RiskLevel.CRITICAL.value
    elif score >= 60:
        return RiskLevel.HIGH.value
    elif score >= 40:
        return RiskLevel.MEDIUM.value
    elif score >= 20:
        return RiskLevel.LOW.value
    return RiskLevel.MINIMAL.value


def _resolve_country(text: str) -> Optional[str]:
    """Resolve country name/alias to ISO code."""
    text_lower = text.strip().lower()
    # Direct ISO code match
    if text_lower.upper() in COUNTRY_RISK_PROFILES:
        return text_lower.upper()
    # Alias match
    for code, profile in COUNTRY_RISK_PROFILES.items():
        if text_lower in profile.get("aliases", []):
            return code
    return None


def _detect_origin_from_listing(title: str, description: str) -> Optional[str]:
    """Try to detect origin country from listing text."""
    combined = f"{title} {description}".lower()
    patterns = [
        r"made\s+in\s+(\w+(?:\s+\w+)?)",
        r"origin:\s*(\w+(?:\s+\w+)?)",
        r"shipped?\s+from\s+(\w+(?:\s+\w+)?)",
        r"manufactured?\s+in\s+(\w+(?:\s+\w+)?)",
        r"产地[：:]\s*(\S+)",
        r"from\s+(\w+(?:\s+\w+)?)\s+factory",
    ]
    for pattern in patterns:
        m = re.search(pattern, combined)
        if m:
            country = _resolve_country(m.group(1))
            if country:
                return country
    return None


def _detect_category(title: str, description: str) -> str:
    """Detect product category from listing text."""
    combined = f"{title} {description}".lower()
    category_keywords = {
        "electronics": ["electronic", "battery", "usb", "bluetooth", "led", "charger",
                        "cable", "adapter", "phone", "tablet", "computer", "speaker"],
        "textiles": ["cotton", "polyester", "fabric", "textile", "clothing", "shirt",
                     "dress", "garment", "sewing", "t-shirt", "hoodie"],
        "food": ["food", "organic", "snack", "tea", "coffee", "spice", "supplement",
                 "vitamin", "nutrition", "edible"],
        "toys": ["toy", "game", "puzzle", "doll", "action figure", "lego", "kids",
                 "children", "play", "plush"],
        "cosmetics": ["cosmetic", "beauty", "skincare", "makeup", "serum", "cream",
                      "lotion", "moisturizer", "perfume", "fragrance"],
        "furniture": ["furniture", "table", "chair", "desk", "shelf", "cabinet",
                      "sofa", "bed", "mattress"],
        "automotive": ["car", "automotive", "vehicle", "motor", "tire", "engine",
                       "brake", "oil", "auto parts"],
        "health": ["medical", "health", "first aid", "mask", "sanitizer", "thermometer",
                   "blood pressure", "health care"],
    }
    for cat, keywords in category_keywords.items():
        if any(kw in combined for kw in keywords):
            return cat
    return "general"


# ---------------------------------------------------------------------------
# Core Analyzer
# ---------------------------------------------------------------------------

class SupplyChainRiskAnalyzer:
    """Analyze supply chain risks for e-commerce listings."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        if db_path:
            self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT,
                overall_score REAL,
                overall_level TEXT,
                resilience_score REAL,
                report_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS disruption_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin_country TEXT,
                category TEXT,
                severity TEXT,
                description TEXT,
                duration_days INTEGER,
                occurred_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def analyze(
        self,
        title: str,
        description: str = "",
        origin_country: Optional[str] = None,
        suppliers: Optional[list[dict]] = None,
        price: float = 0.0,
        category: Optional[str] = None,
        inventory_units: int = 0,
        daily_sales: float = 0.0,
        listing_id: Optional[str] = None,
    ) -> SupplyChainReport:
        """Run complete supply chain risk analysis."""
        # Resolve inputs
        if origin_country:
            resolved = _resolve_country(origin_country)
            if resolved:
                origin_country = resolved
        else:
            origin_country = _detect_origin_from_listing(title, description) or "CN"

        if not category:
            category = _detect_category(title, description)

        cat_mods = CATEGORY_RISK_MODIFIERS.get(category, CATEGORY_RISK_MODIFIERS["general"])

        # Build supplier profiles
        supplier_profiles = []
        if suppliers:
            for s in suppliers:
                sp = SupplierProfile(
                    name=s.get("name", "Unknown"),
                    country=s.get("country", origin_country),
                    share_pct=s.get("share_pct", 100.0 / len(suppliers)),
                    lead_days=s.get("lead_days", 30),
                    quality_score=s.get("quality_score", 70.0),
                    reliability_score=s.get("reliability_score", 70.0),
                    backup_available=s.get("backup_available", False),
                    certifications=s.get("certifications", []),
                )
                supplier_profiles.append(sp)
        else:
            # Single unknown supplier assumption
            country_profile = COUNTRY_RISK_PROFILES.get(origin_country, {})
            supplier_profiles.append(SupplierProfile(
                name="Primary (inferred)",
                country=origin_country,
                share_pct=100.0,
                lead_days=country_profile.get("lead_days", 30),
            ))

        # Analyze risk factors
        risk_factors = []

        # 1. Sourcing risk
        risk_factors.append(self._assess_sourcing_risk(origin_country, cat_mods))

        # 2. Logistics risk
        risk_factors.append(self._assess_logistics_risk(origin_country))

        # 3. Tariff risk
        tariff_factor = self._assess_tariff_risk(origin_country, price, category)
        risk_factors.append(tariff_factor)

        # 4. Supplier concentration
        risk_factors.append(self._assess_concentration_risk(supplier_profiles))

        # 5. Quality risk
        risk_factors.append(self._assess_quality_risk(supplier_profiles, cat_mods))

        # 6. Lead time risk
        lead_estimate = self._estimate_lead_time(origin_country, category)
        risk_factors.append(self._assess_lead_time_risk(lead_estimate))

        # 7. Inventory risk
        if inventory_units > 0 and daily_sales > 0:
            risk_factors.append(self._assess_inventory_risk(
                inventory_units, daily_sales, lead_estimate))

        # 8. Compliance risk
        risk_factors.append(self._assess_compliance_risk(category, origin_country, cat_mods))

        # 9. Geopolitical risk
        risk_factors.append(self._assess_geopolitical_risk(origin_country))

        # 10. Demand volatility
        risk_factors.append(self._assess_demand_volatility(category, price))

        # Calculate overall scores
        weights = {
            RiskCategory.SOURCING.value: 1.2,
            RiskCategory.LOGISTICS.value: 1.0,
            RiskCategory.TARIFF.value: 1.3,
            RiskCategory.SUPPLIER_CONCENTRATION.value: 1.5,
            RiskCategory.QUALITY.value: 1.1,
            RiskCategory.LEAD_TIME.value: 1.0,
            RiskCategory.INVENTORY.value: 0.9,
            RiskCategory.COMPLIANCE.value: 1.2,
            RiskCategory.GEOPOLITICAL.value: 0.8,
            RiskCategory.DEMAND_VOLATILITY.value: 0.7,
        }

        total_weight = sum(weights.get(rf.category, 1.0) for rf in risk_factors)
        weighted_sum = sum(rf.score * weights.get(rf.category, 1.0) for rf in risk_factors)
        overall_score = weighted_sum / total_weight if total_weight > 0 else 50.0

        # Resilience = inverse of concentration + supplier quality + backup availability
        resilience = self._calculate_resilience(supplier_profiles, risk_factors)

        # Seasonal risks
        seasonal = self._get_seasonal_risks()

        # Mitigations
        mitigations = self._generate_mitigations(risk_factors, supplier_profiles, origin_country)

        # Tariff impact detail
        tariff_impact = self._calculate_tariff_impact(origin_country, price, category)

        # Alternative sources
        alternatives = self._suggest_alternatives(origin_country, category)

        report = SupplyChainReport(
            overall_score=overall_score,
            overall_level=_score_to_level(overall_score),
            resilience_score=resilience,
            risk_factors=risk_factors,
            suppliers=supplier_profiles,
            lead_time=lead_estimate,
            seasonal_risks=seasonal,
            mitigations=mitigations,
            tariff_impact=tariff_impact,
            alternative_sources=alternatives,
        )

        # Persist if db configured
        if self.db_path and listing_id:
            self._save_assessment(listing_id, report)

        return report

    # ── Risk assessment methods ──────────────────────────

    def _assess_sourcing_risk(self, country: str, cat_mods: dict) -> RiskFactor:
        profile = COUNTRY_RISK_PROFILES.get(country, {})
        stability = profile.get("stability", 50)
        # Lower stability = higher risk
        score = (100 - stability) * cat_mods.get("quality_risk", 1.0)
        return RiskFactor(
            category=RiskCategory.SOURCING.value,
            name="Sourcing Origin Risk",
            score=min(score, 100),
            description=f"Origin: {country}, stability index: {stability}/100",
            mitigation="Diversify sourcing across 2-3 countries",
            impact="Supply disruption could halt listings for weeks",
        )

    def _assess_logistics_risk(self, country: str) -> RiskFactor:
        profile = COUNTRY_RISK_PROFILES.get(country, {})
        logistics = profile.get("logistics", 50)
        score = 100 - logistics
        return RiskFactor(
            category=RiskCategory.LOGISTICS.value,
            name="Logistics Infrastructure",
            score=score,
            description=f"Logistics index: {logistics}/100 for {country}",
            mitigation="Use multiple shipping routes; consider air freight for urgent orders",
            impact="Delayed shipments lead to stockouts and lost sales",
        )

    def _assess_tariff_risk(self, country: str, price: float, category: str) -> RiskFactor:
        profile = COUNTRY_RISK_PROFILES.get(country, {})
        tariff_base = profile.get("tariff_risk", 50)
        # High-value items have more tariff exposure
        if price > 100:
            tariff_base = min(100, tariff_base * 1.2)
        elif price > 50:
            tariff_base = min(100, tariff_base * 1.1)
        return RiskFactor(
            category=RiskCategory.TARIFF.value,
            name="Tariff & Trade Risk",
            score=tariff_base,
            description=f"Tariff risk index: {tariff_base:.0f}/100, origin: {country}",
            mitigation="Explore tariff engineering, bonded warehouses, or FTZ routing",
            impact=f"Potential {tariff_base*0.3:.0f}% cost increase from tariff changes",
        )

    def _assess_concentration_risk(self, suppliers: list[SupplierProfile]) -> RiskFactor:
        if not suppliers:
            return RiskFactor(
                category=RiskCategory.SUPPLIER_CONCENTRATION.value,
                name="Supplier Concentration",
                score=90,
                description="No supplier data available — extreme concentration risk",
                mitigation="Identify and qualify at least 2 backup suppliers",
            )
        max_share = max(s.share_pct for s in suppliers)
        n_suppliers = len(suppliers)
        backups = sum(1 for s in suppliers if s.backup_available)

        # HHI (Herfindahl–Hirschman Index) normalized
        hhi = sum((s.share_pct / 100) ** 2 for s in suppliers)
        # HHI ranges from 1/n (perfectly diversified) to 1 (monopoly)

        score = hhi * 100  # Monopoly = 100, diversified = low
        if max_share > 80:
            score = max(score, 75)
        if n_suppliers == 1:
            score = max(score, 80)
        if backups == 0:
            score = min(100, score + 15)

        return RiskFactor(
            category=RiskCategory.SUPPLIER_CONCENTRATION.value,
            name="Supplier Concentration",
            score=score,
            description=f"{n_suppliers} supplier(s), max share: {max_share:.0f}%, "
                        f"HHI: {hhi:.2f}, backups: {backups}",
            mitigation="Reduce top supplier to <50% share; qualify backup for each source",
            impact="Single supplier failure = complete supply interruption",
        )

    def _assess_quality_risk(self, suppliers: list[SupplierProfile], cat_mods: dict) -> RiskFactor:
        if not suppliers:
            return RiskFactor(
                category=RiskCategory.QUALITY.value, name="Quality Risk",
                score=60, description="No supplier quality data")

        avg_quality = sum(s.quality_score for s in suppliers) / len(suppliers)
        base_score = (100 - avg_quality) * cat_mods.get("quality_risk", 1.0)
        # Certifications reduce risk
        any_certs = any(s.certifications for s in suppliers)
        if any_certs:
            base_score *= 0.8

        return RiskFactor(
            category=RiskCategory.QUALITY.value,
            name="Quality Control Risk",
            score=min(100, base_score),
            description=f"Avg supplier quality: {avg_quality:.0f}/100, "
                        f"certified: {'yes' if any_certs else 'no'}",
            mitigation="Implement pre-shipment inspections (PSI); require factory certifications",
            impact="Quality issues lead to returns, negative reviews, and listing suspension",
        )

    def _assess_lead_time_risk(self, lead: LeadTimeEstimate) -> RiskFactor:
        total = lead.total_days
        if total > 60:
            score = 85
        elif total > 45:
            score = 65
        elif total > 30:
            score = 45
        elif total > 20:
            score = 25
        else:
            score = 10

        buffer_ratio = lead.buffer_days / lead.minimum_days if lead.minimum_days > 0 else 0
        if buffer_ratio < 0.1:
            score = min(100, score + 15)

        return RiskFactor(
            category=RiskCategory.LEAD_TIME.value,
            name="Lead Time Risk",
            score=score,
            description=f"Total: {total}d (mfg: {lead.manufacturing_days}d + "
                        f"ship: {lead.shipping_days}d + customs: {lead.customs_days}d + "
                        f"buffer: {lead.buffer_days}d)",
            mitigation="Pre-position safety stock; negotiate shorter manufacturing cycles",
            impact="Long lead times amplify stockout risk during demand spikes",
        )

    def _assess_inventory_risk(self, units: int, daily_sales: float,
                                lead: LeadTimeEstimate) -> RiskFactor:
        days_of_stock = units / daily_sales if daily_sales > 0 else 999
        reorder_point = lead.total_days * daily_sales * 1.2  # 20% buffer

        if days_of_stock < lead.total_days:
            score = 90  # Will stockout before reorder arrives
        elif days_of_stock < lead.total_days * 1.5:
            score = 65
        elif days_of_stock < lead.total_days * 2:
            score = 40
        elif days_of_stock > lead.total_days * 5:
            score = 30  # Overstocked — capital risk
        else:
            score = 15

        return RiskFactor(
            category=RiskCategory.INVENTORY.value,
            name="Inventory Coverage Risk",
            score=score,
            description=f"Stock: {units} units, {days_of_stock:.0f} days coverage, "
                        f"reorder point: {reorder_point:.0f} units",
            mitigation="Maintain 2x lead time safety stock; set auto-reorder triggers",
            impact="Stockout loses Buy Box and organic ranking momentum",
        )

    def _assess_compliance_risk(self, category: str, country: str, cat_mods: dict) -> RiskFactor:
        compliance_mod = cat_mods.get("compliance", 1.0)
        base = 30 * compliance_mod  # Base compliance risk

        # Higher compliance risk for regulated categories
        high_compliance = ["food", "health", "cosmetics", "toys", "electronics"]
        if category in high_compliance:
            base = min(100, base + 20)

        return RiskFactor(
            category=RiskCategory.COMPLIANCE.value,
            name="Regulatory Compliance Risk",
            score=min(100, base),
            description=f"Category: {category}, compliance modifier: {compliance_mod:.1f}x",
            mitigation="Verify FDA/CE/FCC certifications; use compliant labeling and packaging",
            impact="Non-compliance = listing removal, fines, and import seizures",
        )

    def _assess_geopolitical_risk(self, country: str) -> RiskFactor:
        profile = COUNTRY_RISK_PROFILES.get(country, {})
        stability = profile.get("stability", 50)
        score = max(0, 85 - stability)  # Inverse of stability

        return RiskFactor(
            category=RiskCategory.GEOPOLITICAL.value,
            name="Geopolitical Stability Risk",
            score=score,
            description=f"Country: {country}, political stability: {stability}/100",
            mitigation="Maintain buffer inventory; develop alternative supply routes",
            impact="Geopolitical events can freeze trade routes overnight",
        )

    def _assess_demand_volatility(self, category: str, price: float) -> RiskFactor:
        # Higher-priced items and seasonal categories have more volatility
        base = 35
        if category in ["toys", "electronics"]:
            base += 20
        if price > 100:
            base += 10
        elif price < 10:
            base -= 5

        return RiskFactor(
            category=RiskCategory.DEMAND_VOLATILITY.value,
            name="Demand Volatility",
            score=min(100, max(0, base)),
            description=f"Category: {category}, price point: ${price:.2f}",
            mitigation="Use demand forecasting tools; maintain flexible MOQ with suppliers",
            impact="Demand spikes without supply flexibility = lost revenue",
        )

    # ── Estimation & suggestion methods ──────────────────

    def _estimate_lead_time(self, country: str, category: str) -> LeadTimeEstimate:
        profile = COUNTRY_RISK_PROFILES.get(country, {})
        base_lead = profile.get("lead_days", 30)
        region = profile.get("region", "china")

        mfg_days = max(7, int(base_lead * 0.4))
        ship_days = max(5, int(base_lead * 0.45))
        customs_days = 3 if region in ("europe", "north_america") else 5
        buffer = max(3, int(base_lead * 0.15))

        # Category adjustments
        if category in ("electronics", "automotive"):
            mfg_days = int(mfg_days * 1.3)
        elif category in ("textiles", "general"):
            mfg_days = int(mfg_days * 0.9)

        return LeadTimeEstimate(
            manufacturing_days=mfg_days,
            shipping_days=ship_days,
            customs_days=customs_days,
            domestic_transit_days=3,
            buffer_days=buffer,
        )

    def _calculate_resilience(self, suppliers: list[SupplierProfile],
                               risk_factors: list[RiskFactor]) -> float:
        """Calculate supply chain resilience score (0-100, higher = more resilient)."""
        score = 50.0  # Base

        # Supplier diversity bonus
        n = len(suppliers)
        if n >= 3:
            score += 15
        elif n >= 2:
            score += 8

        # Backup availability
        backups = sum(1 for s in suppliers if s.backup_available)
        score += backups * 5

        # Average quality
        if suppliers:
            avg_q = sum(s.quality_score for s in suppliers) / len(suppliers)
            score += (avg_q - 50) * 0.3

        # Penalize for critical/high risks
        critical = sum(1 for r in risk_factors if r.level == "critical")
        high = sum(1 for r in risk_factors if r.level == "high")
        score -= critical * 10
        score -= high * 5

        return max(0.0, min(100.0, score))

    def _get_seasonal_risks(self) -> list[dict]:
        """Get current and upcoming seasonal risks."""
        now = datetime.utcnow()
        risks = []
        for offset in range(3):  # Current + next 2 months
            month = ((now.month - 1 + offset) % 12) + 1
            if month in SEASONAL_RISK_CALENDAR:
                for risk in SEASONAL_RISK_CALENDAR[month]:
                    risks.append({
                        "month": month,
                        "risk": risk.replace("_", " ").title(),
                        "months_away": offset,
                        "urgency": "now" if offset == 0 else f"in {offset} month(s)",
                    })
        return risks

    def _generate_mitigations(self, risk_factors: list[RiskFactor],
                               suppliers: list[SupplierProfile],
                               country: str) -> list[dict]:
        """Generate prioritized mitigation recommendations."""
        mitigations = []
        priority = 0

        # Sort by risk score descending
        sorted_risks = sorted(risk_factors, key=lambda r: r.score, reverse=True)

        for rf in sorted_risks:
            if rf.score < 30:
                continue
            priority += 1
            mitigations.append({
                "priority": priority,
                "category": rf.category,
                "risk_score": round(rf.score, 1),
                "action": rf.mitigation,
                "impact": rf.impact,
                "urgency": "immediate" if rf.score >= 80 else
                          "short_term" if rf.score >= 60 else "planned",
            })

        # Generic high-value mitigations
        if len(suppliers) < 2:
            mitigations.append({
                "priority": 1,
                "category": "strategic",
                "risk_score": 0,
                "action": "Qualify at least 1 backup supplier in a different country",
                "impact": "Eliminates single-point-of-failure risk",
                "urgency": "immediate",
            })

        return mitigations

    def _calculate_tariff_impact(self, country: str, price: float,
                                  category: str) -> dict:
        """Estimate tariff impact on margins."""
        profile = COUNTRY_RISK_PROFILES.get(country, {})
        tariff_risk = profile.get("tariff_risk", 50)

        # Estimate tariff rate range
        base_rate = tariff_risk * 0.25  # Max ~25% for high-risk origins
        current_estimate = base_rate * 0.6
        worst_case = base_rate

        cost_impact_current = price * (current_estimate / 100) if price > 0 else 0
        cost_impact_worst = price * (worst_case / 100) if price > 0 else 0

        return {
            "origin": country,
            "estimated_rate_pct": round(current_estimate, 1),
            "worst_case_rate_pct": round(worst_case, 1),
            "per_unit_impact_current": round(cost_impact_current, 2),
            "per_unit_impact_worst": round(cost_impact_worst, 2),
            "mitigation_options": [
                "First Sale Rule for customs valuation",
                "Tariff engineering (HTS classification optimization)",
                "Foreign Trade Zone (FTZ) benefits",
                f"Shift sourcing to lower-tariff origins" if tariff_risk > 40 else
                "Current origin has favorable tariff status",
            ],
        }

    def _suggest_alternatives(self, current: str, category: str) -> list[dict]:
        """Suggest alternative sourcing countries."""
        current_profile = COUNTRY_RISK_PROFILES.get(current, {})
        current_region = current_profile.get("region", "")
        alternatives = []

        for code, profile in COUNTRY_RISK_PROFILES.items():
            if code == current:
                continue
            # Calculate composite attractiveness
            attractiveness = (
                profile["stability"] * 0.3 +
                profile["logistics"] * 0.3 +
                (100 - profile["tariff_risk"]) * 0.25 +
                (1 if profile["region"] != current_region else 0) * 15  # Diversity bonus
            )
            alternatives.append({
                "country": code,
                "region": profile["region"],
                "attractiveness_score": round(attractiveness, 1),
                "lead_days": profile["lead_days"],
                "tariff_risk": profile["tariff_risk"],
                "logistics_score": profile["logistics"],
                "diversification": profile["region"] != current_region,
            })

        # Sort by attractiveness, return top 5
        alternatives.sort(key=lambda x: x["attractiveness_score"], reverse=True)
        return alternatives[:5]

    # ── Persistence ──────────────────────────────────────

    def _save_assessment(self, listing_id: str, report: SupplyChainReport):
        if not self.db_path:
            return
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO risk_assessments (listing_id, overall_score, overall_level, "
            "resilience_score, report_json) VALUES (?, ?, ?, ?, ?)",
            (listing_id, report.overall_score, report.overall_level,
             report.resilience_score, json.dumps(report.to_dict(), ensure_ascii=False)),
        )
        conn.commit()
        conn.close()

    def get_history(self, listing_id: str, limit: int = 10) -> list[dict]:
        """Get historical risk assessments for a listing."""
        if not self.db_path:
            return []
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT overall_score, overall_level, resilience_score, created_at "
            "FROM risk_assessments WHERE listing_id = ? ORDER BY created_at DESC LIMIT ?",
            (listing_id, limit),
        ).fetchall()
        conn.close()
        return [
            {"score": r[0], "level": r[1], "resilience": r[2], "date": r[3]}
            for r in rows
        ]

    def log_disruption(self, country: str, category: str, severity: str,
                       description: str, duration_days: int = 0):
        """Log a supply chain disruption event."""
        if not self.db_path:
            return
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO disruption_log (origin_country, category, severity, "
            "description, duration_days) VALUES (?, ?, ?, ?, ?)",
            (country, category, severity, description, duration_days),
        )
        conn.commit()
        conn.close()

    def get_disruptions(self, country: Optional[str] = None,
                        limit: int = 20) -> list[dict]:
        """Get disruption history."""
        if not self.db_path:
            return []
        conn = sqlite3.connect(self.db_path)
        if country:
            rows = conn.execute(
                "SELECT origin_country, category, severity, description, "
                "duration_days, occurred_at FROM disruption_log "
                "WHERE origin_country = ? ORDER BY occurred_at DESC LIMIT ?",
                (country, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT origin_country, category, severity, description, "
                "duration_days, occurred_at FROM disruption_log "
                "ORDER BY occurred_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [
            {"country": r[0], "category": r[1], "severity": r[2],
             "description": r[3], "duration_days": r[4], "date": r[5]}
            for r in rows
        ]
