"""
Listing Hijack Detector – Monitor and detect unauthorized sellers, Buy Box loss,
price manipulation, and counterfeit risk on marketplace listings.

Features:
- Buy Box ownership tracking (who holds it, win rate)
- Unauthorized seller detection (whitelist vs actual sellers)
- Price manipulation alerts (suspicious undercuts, MAP violations)
- Counterfeit risk scoring (seller reputation, pricing anomalies)
- Alert generation with severity levels
- Seller history tracking
"""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    BUYBOX_LOST = "buybox_lost"
    UNAUTHORIZED_SELLER = "unauthorized_seller"
    PRICE_UNDERCUT = "price_undercut"
    MAP_VIOLATION = "map_violation"
    COUNTERFEIT_RISK = "counterfeit_risk"
    LISTING_CHANGE = "listing_change"
    REVIEW_MANIPULATION = "review_manipulation"
    SELLER_SURGE = "seller_surge"


@dataclass
class SellerRecord:
    """Track a single seller on a listing."""
    seller_id: str
    seller_name: str
    price: float
    is_fba: bool = False
    rating: float = 0.0
    review_count: int = 0
    first_seen: str = ""
    last_seen: str = ""
    is_authorized: bool = False
    country: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BuyBoxStatus:
    """Buy Box ownership analysis."""
    asin: str
    current_owner: Optional[str]
    owner_price: float
    your_price: float
    you_own_buybox: bool
    win_rate_pct: float
    total_checks: int
    your_wins: int
    competitors_on_listing: int
    lowest_price: float
    highest_price: float
    price_spread_pct: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HijackAlert:
    """A single hijack/violation alert."""
    alert_id: str
    alert_type: str
    severity: str
    asin: str
    title: str
    description: str
    seller: Optional[str]
    detected_at: str
    recommended_action: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CounterfeitRisk:
    """Counterfeit risk assessment for a seller."""
    seller_id: str
    seller_name: str
    risk_score: float   # 0-100
    risk_level: str     # low/medium/high/critical
    factors: list[str]
    price_vs_avg: float
    account_age_days: Optional[int]
    rating: float
    review_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ListingHealth:
    """Overall listing protection health."""
    asin: str
    health_score: float  # 0-100
    total_sellers: int
    authorized_sellers: int
    unauthorized_sellers: int
    buybox_win_rate: float
    active_alerts: int
    risk_level: str
    recommendations: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class HijackDetector:
    """Listing hijack detection and monitoring engine."""

    def __init__(self, your_seller_id: str = "your_store"):
        self.your_seller_id = your_seller_id
        self.authorized_sellers: dict[str, set[str]] = {}  # asin -> set of seller_ids
        self.seller_history: dict[str, list[SellerRecord]] = {}  # asin -> records
        self.buybox_history: dict[str, list[dict]] = {}  # asin -> [{owner, price, ts}]
        self.alerts: list[HijackAlert] = []
        self.map_prices: dict[str, float] = {}  # asin -> minimum advertised price

    def set_authorized_sellers(self, asin: str, seller_ids: list[str]) -> None:
        """Set whitelist of authorized sellers for an ASIN."""
        self.authorized_sellers[asin] = set(seller_ids)
        if self.your_seller_id not in self.authorized_sellers[asin]:
            self.authorized_sellers[asin].add(self.your_seller_id)

    def set_map_price(self, asin: str, map_price: float) -> None:
        """Set Minimum Advertised Price for an ASIN."""
        if map_price <= 0:
            raise ValueError("MAP price must be positive")
        self.map_prices[asin] = map_price

    def _generate_alert_id(self, alert_type: str, asin: str, seller: str = "") -> str:
        """Generate deterministic alert ID."""
        raw = f"{alert_type}:{asin}:{seller}:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        asin: str,
        title: str,
        description: str,
        seller: Optional[str] = None,
        recommended_action: str = "",
        data: Optional[dict] = None,
    ) -> HijackAlert:
        """Create and store an alert."""
        alert = HijackAlert(
            alert_id=self._generate_alert_id(alert_type.value, asin, seller or ""),
            alert_type=alert_type.value,
            severity=severity.value,
            asin=asin,
            title=title,
            description=description,
            seller=seller,
            detected_at=datetime.now(timezone.utc).isoformat(),
            recommended_action=recommended_action,
            data=data or {},
        )
        self.alerts.append(alert)
        return alert

    def check_sellers(
        self, asin: str, current_sellers: list[dict]
    ) -> list[HijackAlert]:
        """
        Check current sellers against whitelist.

        Each seller dict: {seller_id, seller_name, price, is_fba, rating, review_count, country}
        """
        alerts: list[HijackAlert] = []
        records = []

        for s in current_sellers:
            record = SellerRecord(
                seller_id=s.get("seller_id", ""),
                seller_name=s.get("seller_name", ""),
                price=s.get("price", 0),
                is_fba=s.get("is_fba", False),
                rating=s.get("rating", 0),
                review_count=s.get("review_count", 0),
                first_seen=datetime.now(timezone.utc).isoformat(),
                last_seen=datetime.now(timezone.utc).isoformat(),
                country=s.get("country", ""),
            )
            records.append(record)

            # Check authorized
            if asin in self.authorized_sellers:
                if record.seller_id not in self.authorized_sellers[asin]:
                    alert = self._create_alert(
                        AlertType.UNAUTHORIZED_SELLER,
                        AlertSeverity.HIGH,
                        asin,
                        f"Unauthorized seller: {record.seller_name}",
                        f"Seller '{record.seller_name}' ({record.seller_id}) is selling "
                        f"on ASIN {asin} at ${record.price:.2f} but is NOT on the "
                        f"authorized seller list.",
                        seller=record.seller_id,
                        recommended_action="Send cease & desist, file brand registry complaint",
                        data=record.to_dict(),
                    )
                    alerts.append(alert)

            # Check MAP violation
            if asin in self.map_prices:
                map_price = self.map_prices[asin]
                if record.price < map_price:
                    violation_pct = round(
                        (map_price - record.price) / map_price * 100, 2
                    )
                    severity = (
                        AlertSeverity.CRITICAL
                        if violation_pct > 20
                        else AlertSeverity.HIGH
                        if violation_pct > 10
                        else AlertSeverity.MEDIUM
                    )
                    alert = self._create_alert(
                        AlertType.MAP_VIOLATION,
                        severity,
                        asin,
                        f"MAP violation by {record.seller_name}",
                        f"Seller '{record.seller_name}' is selling at ${record.price:.2f}, "
                        f"which is {violation_pct}% below MAP (${map_price:.2f}).",
                        seller=record.seller_id,
                        recommended_action="Contact seller about MAP policy, escalate to brand registry",
                        data={"price": record.price, "map_price": map_price, "violation_pct": violation_pct},
                    )
                    alerts.append(alert)

        # Check for seller surge
        prev_count = len(self.seller_history.get(asin, []))
        if prev_count > 0 and len(current_sellers) > prev_count * 1.5:
            alert = self._create_alert(
                AlertType.SELLER_SURGE,
                AlertSeverity.MEDIUM,
                asin,
                f"Seller surge on {asin}",
                f"Number of sellers increased from {prev_count} to {len(current_sellers)} "
                f"({len(current_sellers) - prev_count} new sellers).",
                recommended_action="Review new sellers for authorization and counterfeit risk",
                data={"previous": prev_count, "current": len(current_sellers)},
            )
            alerts.append(alert)

        self.seller_history[asin] = records
        return alerts

    def check_buybox(
        self,
        asin: str,
        buybox_owner_id: Optional[str],
        buybox_price: float,
        your_price: float,
    ) -> BuyBoxStatus:
        """Track Buy Box ownership and detect loss."""
        # Record history
        if asin not in self.buybox_history:
            self.buybox_history[asin] = []

        self.buybox_history[asin].append({
            "owner": buybox_owner_id,
            "price": buybox_price,
            "your_price": your_price,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        # Calculate win rate
        history = self.buybox_history[asin]
        total = len(history)
        wins = sum(1 for h in history if h["owner"] == self.your_seller_id)
        win_rate = round(wins / total * 100, 2) if total > 0 else 0

        you_own = buybox_owner_id == self.your_seller_id

        # Get seller prices
        sellers = self.seller_history.get(asin, [])
        prices = [s.price for s in sellers if s.price > 0]
        if not prices:
            prices = [buybox_price]

        lowest = min(prices)
        highest = max(prices)
        spread = round((highest - lowest) / lowest * 100, 2) if lowest > 0 else 0

        status = BuyBoxStatus(
            asin=asin,
            current_owner=buybox_owner_id,
            owner_price=buybox_price,
            your_price=your_price,
            you_own_buybox=you_own,
            win_rate_pct=win_rate,
            total_checks=total,
            your_wins=wins,
            competitors_on_listing=len(sellers),
            lowest_price=lowest,
            highest_price=highest,
            price_spread_pct=spread,
        )

        # Alert on buybox loss
        if not you_own and total >= 2:
            prev = history[-2]
            if prev["owner"] == self.your_seller_id:
                self._create_alert(
                    AlertType.BUYBOX_LOST,
                    AlertSeverity.HIGH,
                    asin,
                    f"Buy Box lost on {asin}",
                    f"You lost the Buy Box to '{buybox_owner_id}' at ${buybox_price:.2f}. "
                    f"Your price: ${your_price:.2f}. Win rate: {win_rate}%.",
                    seller=buybox_owner_id,
                    recommended_action="Review pricing strategy, check competitor offers",
                    data=status.to_dict(),
                )

        return status

    def assess_counterfeit_risk(
        self, asin: str, seller: dict, avg_price: float
    ) -> CounterfeitRisk:
        """
        Assess counterfeit risk for a specific seller.

        seller: {seller_id, seller_name, price, rating, review_count, account_age_days, is_fba, country}
        """
        score = 0.0
        factors: list[str] = []

        price = seller.get("price", 0)
        rating = seller.get("rating", 0)
        reviews = seller.get("review_count", 0)
        age_days = seller.get("account_age_days")
        is_fba = seller.get("is_fba", False)

        price_vs_avg = round(
            (price - avg_price) / avg_price * 100, 2
        ) if avg_price > 0 else 0

        # Price suspiciously low (>30% below avg)
        if price_vs_avg < -30:
            score += 35
            factors.append(f"Price {abs(price_vs_avg):.0f}% below average (${price:.2f} vs ${avg_price:.2f})")
        elif price_vs_avg < -20:
            score += 20
            factors.append(f"Price {abs(price_vs_avg):.0f}% below average")
        elif price_vs_avg < -10:
            score += 10
            factors.append(f"Price slightly below average ({abs(price_vs_avg):.0f}%)")

        # Low seller rating
        if rating < 3.0:
            score += 25
            factors.append(f"Very low seller rating ({rating})")
        elif rating < 3.5:
            score += 15
            factors.append(f"Below-average seller rating ({rating})")
        elif rating < 4.0:
            score += 5
            factors.append(f"Moderate seller rating ({rating})")

        # Few reviews
        if reviews < 10:
            score += 20
            factors.append(f"Very few seller reviews ({reviews})")
        elif reviews < 50:
            score += 10
            factors.append(f"Limited seller reviews ({reviews})")

        # New account
        if age_days is not None:
            if age_days < 30:
                score += 20
                factors.append(f"Very new account ({age_days} days)")
            elif age_days < 90:
                score += 10
                factors.append(f"Relatively new account ({age_days} days)")

        # Not FBA (less accountability)
        if not is_fba:
            score += 5
            factors.append("Not using FBA (harder to verify)")

        # Unauthorized
        if asin in self.authorized_sellers:
            sid = seller.get("seller_id", "")
            if sid and sid not in self.authorized_sellers[asin]:
                score += 15
                factors.append("Not on authorized seller list")

        score = min(score, 100)

        if score >= 75:
            level = "critical"
        elif score >= 50:
            level = "high"
        elif score >= 25:
            level = "medium"
        else:
            level = "low"

        risk = CounterfeitRisk(
            seller_id=seller.get("seller_id", ""),
            seller_name=seller.get("seller_name", ""),
            risk_score=score,
            risk_level=level,
            factors=factors,
            price_vs_avg=price_vs_avg,
            account_age_days=age_days,
            rating=rating,
            review_count=reviews,
        )

        if score >= 50:
            self._create_alert(
                AlertType.COUNTERFEIT_RISK,
                AlertSeverity.CRITICAL if score >= 75 else AlertSeverity.HIGH,
                asin,
                f"Counterfeit risk: {seller.get('seller_name', 'Unknown')}",
                f"Risk score {score}/100. Factors: {'; '.join(factors[:3])}",
                seller=seller.get("seller_id"),
                recommended_action="Investigate seller, consider test purchase, file IP complaint if confirmed",
                data=risk.to_dict(),
            )

        return risk

    def detect_price_undercut(
        self,
        asin: str,
        your_price: float,
        competitor_prices: list[dict],
        threshold_pct: float = 15.0,
    ) -> list[HijackAlert]:
        """Detect suspicious price undercuts."""
        alerts: list[HijackAlert] = []

        for cp in competitor_prices:
            comp_price = cp.get("price", 0)
            seller_name = cp.get("seller_name", "Unknown")
            seller_id = cp.get("seller_id", "")

            if comp_price <= 0 or your_price <= 0:
                continue

            undercut_pct = round((your_price - comp_price) / your_price * 100, 2)

            if undercut_pct >= threshold_pct:
                severity = (
                    AlertSeverity.CRITICAL
                    if undercut_pct >= 40
                    else AlertSeverity.HIGH
                    if undercut_pct >= 25
                    else AlertSeverity.MEDIUM
                )
                alert = self._create_alert(
                    AlertType.PRICE_UNDERCUT,
                    severity,
                    asin,
                    f"Price undercut by {seller_name}",
                    f"Seller '{seller_name}' is {undercut_pct}% below your price "
                    f"(${comp_price:.2f} vs ${your_price:.2f}).",
                    seller=seller_id,
                    recommended_action="Verify product authenticity, check if authorized seller",
                    data={
                        "your_price": your_price,
                        "competitor_price": comp_price,
                        "undercut_pct": undercut_pct,
                    },
                )
                alerts.append(alert)

        return alerts

    def listing_health(self, asin: str) -> ListingHealth:
        """Generate overall listing protection health report."""
        sellers = self.seller_history.get(asin, [])
        total = len(sellers)
        authorized = self.authorized_sellers.get(asin, set())
        auth_count = sum(1 for s in sellers if s.seller_id in authorized)
        unauth_count = total - auth_count if authorized else 0

        bb_history = self.buybox_history.get(asin, [])
        bb_wins = sum(1 for h in bb_history if h["owner"] == self.your_seller_id)
        bb_rate = round(bb_wins / len(bb_history) * 100, 2) if bb_history else 100.0

        asin_alerts = [a for a in self.alerts if a.asin == asin]
        active = len(asin_alerts)

        # Health score calculation
        score = 100.0
        recommendations: list[str] = []

        if unauth_count > 0:
            score -= min(unauth_count * 10, 30)
            recommendations.append(
                f"Remove {unauth_count} unauthorized seller(s) via Brand Registry"
            )

        if bb_rate < 80:
            score -= 20
            recommendations.append("Optimize pricing to improve Buy Box win rate")
        elif bb_rate < 95:
            score -= 10
            recommendations.append("Monitor Buy Box — win rate slightly below optimal")

        critical_alerts = sum(
            1 for a in asin_alerts if a.severity == "critical"
        )
        high_alerts = sum(1 for a in asin_alerts if a.severity == "high")
        score -= critical_alerts * 15 + high_alerts * 10

        if total > 5:
            score -= min((total - 5) * 3, 15)
            recommendations.append(
                f"High seller count ({total}) — consider enforcing distribution"
            )

        if not authorized:
            recommendations.append(
                "Set up authorized seller whitelist for proactive monitoring"
            )

        score = max(score, 0)

        if score >= 80:
            risk = "low"
        elif score >= 60:
            risk = "medium"
        elif score >= 40:
            risk = "high"
        else:
            risk = "critical"

        return ListingHealth(
            asin=asin,
            health_score=round(score, 1),
            total_sellers=total,
            authorized_sellers=auth_count,
            unauthorized_sellers=unauth_count,
            buybox_win_rate=bb_rate,
            active_alerts=active,
            risk_level=risk,
            recommendations=recommendations,
        )

    def get_alerts(
        self,
        asin: Optional[str] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[HijackAlert]:
        """Get filtered alerts."""
        filtered = self.alerts
        if asin:
            filtered = [a for a in filtered if a.asin == asin]
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]
        return filtered[-limit:]

    def clear_alerts(self, asin: Optional[str] = None) -> int:
        """Clear alerts, optionally for a specific ASIN."""
        if asin:
            before = len(self.alerts)
            self.alerts = [a for a in self.alerts if a.asin != asin]
            return before - len(self.alerts)
        else:
            count = len(self.alerts)
            self.alerts.clear()
            return count
