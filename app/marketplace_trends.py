"""Marketplace Trends Analyzer - track trending keywords, categories, and niches across platforms.

Provides cross-platform trend detection, keyword velocity scoring,
seasonal pattern recognition, and niche opportunity discovery.
"""

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class TrendDirection(str, Enum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    BREAKOUT = "breakout"
    NEW = "new"


class NicheStatus(str, Enum):
    EMERGING = "emerging"
    GROWING = "growing"
    MATURE = "mature"
    SATURATED = "saturated"
    DECLINING = "declining"


@dataclass
class TrendDataPoint:
    keyword: str
    platform: str
    volume: int
    competition: float  # 0.0-1.0
    timestamp: str
    category: str = ""
    region: str = "global"
    source: str = "manual"


@dataclass
class TrendAnalysis:
    keyword: str
    platform: str
    direction: TrendDirection
    velocity: float  # rate of change, -1.0 to 1.0+
    current_volume: int
    avg_volume: float
    peak_volume: int
    competition: float
    opportunity_score: float  # 0-100
    first_seen: str
    data_points: int
    seasonal_pattern: Optional[str] = None
    related_keywords: list = field(default_factory=list)


@dataclass
class NicheOpportunity:
    niche: str
    status: NicheStatus
    score: float  # 0-100
    platforms: list = field(default_factory=list)
    top_keywords: list = field(default_factory=list)
    avg_competition: float = 0.0
    growth_rate: float = 0.0
    estimated_demand: str = "unknown"
    recommendation: str = ""


@dataclass
class CrossPlatformTrend:
    keyword: str
    platforms: dict = field(default_factory=dict)  # platform -> TrendAnalysis
    global_direction: TrendDirection = TrendDirection.STABLE
    platform_agreement: float = 0.0  # 0-1, how many platforms agree on direction
    best_platform: str = ""
    arbitrage_opportunity: bool = False
    combined_score: float = 0.0


class TrendsDatabase:
    """SQLite-backed trend data storage."""

    def __init__(self, db_path: str = "trends.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS trend_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                platform TEXT NOT NULL,
                volume INTEGER DEFAULT 0,
                competition REAL DEFAULT 0.0,
                category TEXT DEFAULT '',
                region TEXT DEFAULT 'global',
                source TEXT DEFAULT 'manual',
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS niche_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                niche TEXT NOT NULL,
                status TEXT NOT NULL,
                score REAL DEFAULT 0.0,
                platforms TEXT DEFAULT '[]',
                keywords TEXT DEFAULT '[]',
                avg_competition REAL DEFAULT 0.0,
                growth_rate REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS keyword_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                related_keyword TEXT NOT NULL,
                strength REAL DEFAULT 0.0,
                platform TEXT DEFAULT 'all',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(keyword, related_keyword, platform)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_trend_keyword ON trend_data(keyword)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_trend_platform ON trend_data(platform)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_trend_timestamp ON trend_data(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_niche_name ON niche_snapshots(niche)")
        conn.commit()
        conn.close()

    def add_data_point(self, point: TrendDataPoint) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO trend_data (keyword, platform, volume, competition, category, region, source, timestamp) VALUES (?,?,?,?,?,?,?,?)",
            (point.keyword.lower().strip(), point.platform.lower(), point.volume,
             point.competition, point.category, point.region, point.source, point.timestamp),
        )
        row_id = c.lastrowid
        conn.commit()
        conn.close()
        return row_id

    def add_bulk_data(self, points: list[TrendDataPoint]) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        rows = [
            (p.keyword.lower().strip(), p.platform.lower(), p.volume,
             p.competition, p.category, p.region, p.source, p.timestamp)
            for p in points
        ]
        c.executemany(
            "INSERT INTO trend_data (keyword, platform, volume, competition, category, region, source, timestamp) VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
        count = c.rowcount
        conn.commit()
        conn.close()
        return count

    def get_keyword_history(self, keyword: str, platform: str = None, days: int = 90) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        if platform:
            rows = conn.execute(
                "SELECT * FROM trend_data WHERE keyword=? AND platform=? AND timestamp>=? ORDER BY timestamp",
                (keyword.lower().strip(), platform.lower(), cutoff),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trend_data WHERE keyword=? AND timestamp>=? ORDER BY timestamp",
                (keyword.lower().strip(), cutoff),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_top_keywords(self, platform: str = None, limit: int = 20, days: int = 30) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        if platform:
            rows = conn.execute(
                """SELECT keyword, platform, AVG(volume) as avg_vol, MAX(volume) as max_vol,
                   AVG(competition) as avg_comp, COUNT(*) as data_points
                   FROM trend_data WHERE platform=? AND timestamp>=?
                   GROUP BY keyword, platform ORDER BY avg_vol DESC LIMIT ?""",
                (platform.lower(), cutoff, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT keyword, GROUP_CONCAT(DISTINCT platform) as platforms,
                   AVG(volume) as avg_vol, MAX(volume) as max_vol,
                   AVG(competition) as avg_comp, COUNT(*) as data_points
                   FROM trend_data WHERE timestamp>=?
                   GROUP BY keyword ORDER BY avg_vol DESC LIMIT ?""",
                (cutoff, limit),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_keyword_relation(self, keyword: str, related: str, strength: float, platform: str = "all"):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO keyword_relations (keyword, related_keyword, strength, platform)
               VALUES (?,?,?,?)""",
            (keyword.lower(), related.lower(), strength, platform),
        )
        conn.commit()
        conn.close()

    def get_related_keywords(self, keyword: str, limit: int = 10) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM keyword_relations WHERE keyword=? ORDER BY strength DESC LIMIT ?",
            (keyword.lower(), limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_niche_snapshot(self, niche: NicheOpportunity, timestamp: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO niche_snapshots (niche, status, score, platforms, keywords,
               avg_competition, growth_rate, timestamp)
               VALUES (?,?,?,?,?,?,?,?)""",
            (niche.niche, niche.status.value, niche.score,
             json.dumps(niche.platforms), json.dumps(niche.top_keywords),
             niche.avg_competition, niche.growth_rate, timestamp),
        )
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        total_points = c.execute("SELECT COUNT(*) FROM trend_data").fetchone()[0]
        unique_keywords = c.execute("SELECT COUNT(DISTINCT keyword) FROM trend_data").fetchone()[0]
        platforms = c.execute("SELECT COUNT(DISTINCT platform) FROM trend_data").fetchone()[0]
        relations = c.execute("SELECT COUNT(*) FROM keyword_relations").fetchone()[0]
        niches = c.execute("SELECT COUNT(*) FROM niche_snapshots").fetchone()[0]
        conn.close()
        return {
            "total_data_points": total_points,
            "unique_keywords": unique_keywords,
            "platforms_tracked": platforms,
            "keyword_relations": relations,
            "niche_snapshots": niches,
        }


class TrendAnalyzer:
    """Analyze keyword and category trends across platforms."""

    SUPPORTED_PLATFORMS = ["amazon", "shopee", "lazada", "aliexpress", "ebay", "walmart", "temu", "etsy"]

    SEASONAL_PATTERNS = {
        "q1_peak": {"months": [1, 2, 3], "label": "Q1 Peak (New Year / CNY)"},
        "summer": {"months": [6, 7, 8], "label": "Summer Season"},
        "back_to_school": {"months": [8, 9], "label": "Back to School"},
        "q4_holiday": {"months": [10, 11, 12], "label": "Q4 Holiday (BF/CM/Christmas)"},
        "valentines": {"months": [1, 2], "label": "Valentine's Season"},
        "spring": {"months": [3, 4, 5], "label": "Spring Season"},
    }

    def __init__(self, db: TrendsDatabase = None):
        self.db = db or TrendsDatabase()

    def analyze_keyword(self, keyword: str, platform: str = None, days: int = 90) -> TrendAnalysis:
        """Analyze trend for a specific keyword."""
        history = self.db.get_keyword_history(keyword, platform, days)
        if not history:
            return TrendAnalysis(
                keyword=keyword,
                platform=platform or "all",
                direction=TrendDirection.NEW,
                velocity=0.0,
                current_volume=0,
                avg_volume=0.0,
                peak_volume=0,
                competition=0.0,
                opportunity_score=0.0,
                first_seen=datetime.utcnow().isoformat(),
                data_points=0,
            )

        volumes = [h["volume"] for h in history]
        competitions = [h["competition"] for h in history]
        current_vol = volumes[-1] if volumes else 0
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        peak_vol = max(volumes) if volumes else 0
        avg_comp = sum(competitions) / len(competitions) if competitions else 0

        velocity = self._calculate_velocity(volumes)
        direction = self._determine_direction(velocity, volumes)
        seasonal = self._detect_seasonal_pattern(history)
        opportunity = self._calculate_opportunity_score(current_vol, avg_vol, avg_comp, velocity, direction)

        related = self.db.get_related_keywords(keyword, limit=5)
        related_kws = [r["related_keyword"] for r in related]

        return TrendAnalysis(
            keyword=keyword,
            platform=platform or history[0].get("platform", "all"),
            direction=direction,
            velocity=round(velocity, 4),
            current_volume=current_vol,
            avg_volume=round(avg_vol, 1),
            peak_volume=peak_vol,
            competition=round(avg_comp, 3),
            opportunity_score=round(opportunity, 1),
            first_seen=history[0]["timestamp"],
            data_points=len(history),
            seasonal_pattern=seasonal,
            related_keywords=related_kws,
        )

    def _calculate_velocity(self, volumes: list[int]) -> float:
        """Calculate rate of change (-1.0 to 1.0+)."""
        if len(volumes) < 2:
            return 0.0
        recent = volumes[-min(5, len(volumes)):]
        older = volumes[:max(1, len(volumes) // 2)]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        if avg_older == 0:
            return 1.0 if avg_recent > 0 else 0.0
        return (avg_recent - avg_older) / avg_older

    def _determine_direction(self, velocity: float, volumes: list[int]) -> TrendDirection:
        if len(volumes) < 2:
            return TrendDirection.NEW
        if velocity > 0.5:
            return TrendDirection.BREAKOUT
        elif velocity > 0.1:
            return TrendDirection.RISING
        elif velocity < -0.2:
            return TrendDirection.DECLINING
        return TrendDirection.STABLE

    def _detect_seasonal_pattern(self, history: list[dict]) -> Optional[str]:
        """Detect if keyword follows a seasonal pattern."""
        if len(history) < 6:
            return None
        month_volumes: dict[int, list] = {}
        for h in history:
            try:
                month = datetime.fromisoformat(h["timestamp"]).month
            except (ValueError, KeyError):
                continue
            month_volumes.setdefault(month, []).append(h["volume"])
        if len(month_volumes) < 3:
            return None
        month_avgs = {m: sum(v) / len(v) for m, v in month_volumes.items()}
        overall_avg = sum(month_avgs.values()) / len(month_avgs)
        if overall_avg == 0:
            return None
        for pattern_key, pattern in self.SEASONAL_PATTERNS.items():
            peak_months = pattern["months"]
            peak_avg = sum(month_avgs.get(m, 0) for m in peak_months) / len(peak_months)
            if peak_avg > overall_avg * 1.3:
                return pattern["label"]
        return None

    def _calculate_opportunity_score(
        self, current_vol: int, avg_vol: float, competition: float,
        velocity: float, direction: TrendDirection,
    ) -> float:
        """Score 0-100: higher = better opportunity."""
        score = 50.0
        # Volume component (0-25)
        if avg_vol > 0:
            vol_score = min(25, (current_vol / max(avg_vol, 1)) * 12.5)
            score += vol_score - 12.5
        # Competition component (0-25, low = good)
        comp_score = (1 - competition) * 25
        score += comp_score - 12.5
        # Velocity component (0-25)
        vel_score = min(25, max(0, (velocity + 0.5) * 25))
        score += vel_score - 12.5
        # Direction bonus
        direction_bonus = {
            TrendDirection.BREAKOUT: 15,
            TrendDirection.RISING: 8,
            TrendDirection.NEW: 5,
            TrendDirection.STABLE: 0,
            TrendDirection.DECLINING: -10,
        }
        score += direction_bonus.get(direction, 0)
        return max(0, min(100, score))

    def discover_niches(self, min_keywords: int = 3, days: int = 30) -> list[NicheOpportunity]:
        """Discover niche opportunities from tracked keywords."""
        top_kws = self.db.get_top_keywords(days=days, limit=100)
        if not top_kws:
            return []
        # Group by category
        category_kws: dict[str, list] = {}
        for kw in top_kws:
            history = self.db.get_keyword_history(kw["keyword"], days=days)
            for h in history:
                cat = h.get("category", "uncategorized")
                if cat:
                    category_kws.setdefault(cat, []).append(kw)
                    break
        niches = []
        for cat, keywords in category_kws.items():
            if len(keywords) < min_keywords:
                continue
            avg_comp = sum(k.get("avg_comp", 0) for k in keywords) / len(keywords)
            avg_vol = sum(k.get("avg_vol", 0) for k in keywords) / len(keywords)
            growth_rates = []
            for kw in keywords:
                analysis = self.analyze_keyword(kw["keyword"], days=days)
                growth_rates.append(analysis.velocity)
            avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
            status = self._classify_niche(avg_comp, avg_growth, len(keywords))
            platforms_set = set()
            for kw in keywords:
                if "platforms" in kw:
                    platforms_set.update(kw["platforms"].split(","))
                elif "platform" in kw:
                    platforms_set.add(kw["platform"])
            score = self._score_niche(avg_vol, avg_comp, avg_growth, len(keywords), status)
            top_kw_names = [kw["keyword"] for kw in sorted(keywords, key=lambda x: x.get("avg_vol", 0), reverse=True)[:5]]
            demand = "high" if avg_vol > 10000 else "medium" if avg_vol > 1000 else "low"
            niche = NicheOpportunity(
                niche=cat,
                status=status,
                score=round(score, 1),
                platforms=sorted(platforms_set),
                top_keywords=top_kw_names,
                avg_competition=round(avg_comp, 3),
                growth_rate=round(avg_growth, 4),
                estimated_demand=demand,
                recommendation=self._niche_recommendation(status, score, avg_comp),
            )
            niches.append(niche)
        return sorted(niches, key=lambda n: n.score, reverse=True)

    def _classify_niche(self, competition: float, growth: float, keyword_count: int) -> NicheStatus:
        if growth > 0.3 and competition < 0.3:
            return NicheStatus.EMERGING
        elif growth > 0.1 and competition < 0.6:
            return NicheStatus.GROWING
        elif competition > 0.7 and growth < 0.05:
            return NicheStatus.SATURATED
        elif growth < -0.1:
            return NicheStatus.DECLINING
        return NicheStatus.MATURE

    def _score_niche(self, avg_vol: float, competition: float, growth: float,
                     keyword_count: int, status: NicheStatus) -> float:
        score = 50.0
        score += min(20, (1 - competition) * 20)
        score += min(15, max(-15, growth * 30))
        score += min(10, keyword_count * 2)
        status_bonus = {
            NicheStatus.EMERGING: 10,
            NicheStatus.GROWING: 5,
            NicheStatus.MATURE: 0,
            NicheStatus.SATURATED: -10,
            NicheStatus.DECLINING: -15,
        }
        score += status_bonus.get(status, 0)
        return max(0, min(100, score))

    def _niche_recommendation(self, status: NicheStatus, score: float, competition: float) -> str:
        if status == NicheStatus.EMERGING and score > 70:
            return "🔥 Strong entry opportunity - low competition, rising demand. Act fast!"
        elif status == NicheStatus.GROWING:
            return "✅ Good timing - market growing with moderate competition."
        elif status == NicheStatus.MATURE and competition < 0.5:
            return "💡 Differentiation needed - mature market but gaps exist."
        elif status == NicheStatus.SATURATED:
            return "⚠️ Highly competitive - only enter with strong differentiation or brand."
        elif status == NicheStatus.DECLINING:
            return "🚫 Avoid - declining demand, poor ROI expected."
        return "📊 Neutral - evaluate further before committing."

    def cross_platform_analysis(self, keyword: str, days: int = 90) -> CrossPlatformTrend:
        """Analyze a keyword across all tracked platforms."""
        platform_analyses = {}
        for platform in self.SUPPORTED_PLATFORMS:
            history = self.db.get_keyword_history(keyword, platform, days)
            if history:
                analysis = self.analyze_keyword(keyword, platform, days)
                platform_analyses[platform] = analysis

        if not platform_analyses:
            return CrossPlatformTrend(keyword=keyword)

        directions = [a.direction for a in platform_analyses.values()]
        direction_counts: dict[TrendDirection, int] = {}
        for d in directions:
            direction_counts[d] = direction_counts.get(d, 0) + 1
        global_dir = max(direction_counts, key=direction_counts.get)
        agreement = direction_counts[global_dir] / len(directions)

        best = max(platform_analyses.items(), key=lambda x: x[1].opportunity_score)
        scores = [a.opportunity_score for a in platform_analyses.values()]
        combined = sum(scores) / len(scores)
        comps = [a.competition for a in platform_analyses.values()]
        arbitrage = (max(comps) - min(comps)) > 0.3 if len(comps) > 1 else False

        return CrossPlatformTrend(
            keyword=keyword,
            platforms={k: asdict(v) for k, v in platform_analyses.items()},
            global_direction=global_dir,
            platform_agreement=round(agreement, 2),
            best_platform=best[0],
            arbitrage_opportunity=arbitrage,
            combined_score=round(combined, 1),
        )

    def generate_trend_report(self, days: int = 30, top_n: int = 20) -> dict:
        """Generate comprehensive trend report."""
        top_keywords = self.db.get_top_keywords(days=days, limit=top_n)
        analyses = []
        for kw in top_keywords:
            analysis = self.analyze_keyword(kw["keyword"], days=days)
            analyses.append(asdict(analysis))

        rising = [a for a in analyses if a["direction"] in ("rising", "breakout")]
        declining = [a for a in analyses if a["direction"] == "declining"]
        niches = self.discover_niches(days=days)
        stats = self.db.get_stats()

        return {
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "stats": stats,
            "top_keywords": analyses[:top_n],
            "rising_keywords": sorted(rising, key=lambda a: a["velocity"], reverse=True)[:10],
            "declining_keywords": sorted(declining, key=lambda a: a["velocity"])[:10],
            "niche_opportunities": [asdict(n) for n in niches[:10]],
            "total_analyzed": len(analyses),
        }

    def format_report_text(self, report: dict) -> str:
        """Format report as readable text."""
        lines = ["📊 Marketplace Trends Report", f"Period: {report['period_days']} days", ""]

        if report.get("rising_keywords"):
            lines.append("🔥 Rising Keywords:")
            for kw in report["rising_keywords"][:5]:
                lines.append(f"  ↗️ {kw['keyword']} (velocity: {kw['velocity']:+.1%}, score: {kw['opportunity_score']})")
            lines.append("")

        if report.get("declining_keywords"):
            lines.append("📉 Declining Keywords:")
            for kw in report["declining_keywords"][:5]:
                lines.append(f"  ↘️ {kw['keyword']} (velocity: {kw['velocity']:+.1%})")
            lines.append("")

        if report.get("niche_opportunities"):
            lines.append("💡 Niche Opportunities:")
            for n in report["niche_opportunities"][:5]:
                lines.append(f"  {n['niche']}: {n['status']} (score: {n['score']}, growth: {n['growth_rate']:+.1%})")
                lines.append(f"    → {n['recommendation']}")
            lines.append("")

        stats = report.get("stats", {})
        lines.append(f"📈 Tracked: {stats.get('unique_keywords', 0)} keywords, "
                     f"{stats.get('total_data_points', 0)} data points, "
                     f"{stats.get('platforms_tracked', 0)} platforms")
        return "\n".join(lines)
