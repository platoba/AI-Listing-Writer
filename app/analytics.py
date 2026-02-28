"""SQLite-backed analytics engine.

Tracks listing generation metrics, quality scores, platform trends,
and user productivity for insights and reporting.
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DB_PATH = Path("data/analytics.db")


@contextmanager
def _get_db(db_path: Optional[Path] = None):
    """Context manager for database connections."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None):
    """Initialize analytics database tables."""
    with _get_db(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                product TEXT NOT NULL,
                language TEXT DEFAULT 'English',
                char_count INTEGER DEFAULT 0,
                seo_score REAL DEFAULT 0,
                validation_score REAL DEFAULT 0,
                angle TEXT DEFAULT '',
                duration_ms INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                avg_seo_score REAL DEFAULT 0,
                avg_chars INTEGER DEFAULT 0,
                PRIMARY KEY (date, user_id, platform)
            );

            CREATE TABLE IF NOT EXISTS quality_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                week TEXT NOT NULL,
                avg_seo_score REAL DEFAULT 0,
                avg_validation_score REAL DEFAULT 0,
                total_generations INTEGER DEFAULT 0,
                top_platform TEXT DEFAULT '',
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_gen_user ON generations(user_id);
            CREATE INDEX IF NOT EXISTS idx_gen_platform ON generations(platform);
            CREATE INDEX IF NOT EXISTS idx_gen_date ON generations(created_at);
            CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_stats(date);
        """)


def record_generation(
    user_id: int,
    platform: str,
    product: str,
    language: str = "English",
    char_count: int = 0,
    seo_score: float = 0.0,
    validation_score: float = 0.0,
    angle: str = "",
    duration_ms: int = 0,
    db_path: Optional[Path] = None,
):
    """Record a listing generation event."""
    now = time.time()
    date_str = time.strftime("%Y-%m-%d", time.localtime(now))

    with _get_db(db_path) as conn:
        conn.execute(
            """INSERT INTO generations
               (user_id, platform, product, language, char_count,
                seo_score, validation_score, angle, duration_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, platform, product, language, char_count,
             seo_score, validation_score, angle, duration_ms, now),
        )

        # Update daily stats
        conn.execute(
            """INSERT INTO daily_stats (date, user_id, platform, count, avg_seo_score, avg_chars)
               VALUES (?, ?, ?, 1, ?, ?)
               ON CONFLICT(date, user_id, platform) DO UPDATE SET
                   count = count + 1,
                   avg_seo_score = (avg_seo_score * count + ?) / (count + 1),
                   avg_chars = (avg_chars * count + ?) / (count + 1)""",
            (date_str, user_id, platform, seo_score, char_count,
             seo_score, char_count),
        )


@dataclass
class UserStats:
    user_id: int
    total_generations: int = 0
    platforms: dict[str, int] = field(default_factory=dict)
    avg_seo_score: float = 0.0
    avg_char_count: float = 0.0
    most_used_platform: str = ""
    last_7_days: int = 0
    last_30_days: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    top_products: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"📊 Analytics for User {self.user_id}",
            f"   Total listings: {self.total_generations}",
            f"   Avg SEO score: {self.avg_seo_score:.1f}/100",
            f"   Avg length: {self.avg_char_count:.0f} chars",
            f"   Most used: {self.most_used_platform}",
            f"   Last 7 days: {self.last_7_days}",
            f"   Last 30 days: {self.last_30_days}",
            "",
            "   Platforms:",
        ]
        for p, c in sorted(self.platforms.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"     {p}: {c}")
        if self.languages:
            lines.append("   Languages:")
            for l, c in sorted(self.languages.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"     {l}: {c}")
        return "\n".join(lines)


def get_user_stats(user_id: int, db_path: Optional[Path] = None) -> UserStats:
    """Get comprehensive stats for a user."""
    stats = UserStats(user_id=user_id)

    with _get_db(db_path) as conn:
        # Total and averages
        row = conn.execute(
            """SELECT COUNT(*) as total, AVG(seo_score) as avg_seo,
                      AVG(char_count) as avg_chars
               FROM generations WHERE user_id = ?""",
            (user_id,),
        ).fetchone()
        if row:
            stats.total_generations = row["total"]
            stats.avg_seo_score = row["avg_seo"] or 0.0
            stats.avg_char_count = row["avg_chars"] or 0.0

        # Platform breakdown
        rows = conn.execute(
            """SELECT platform, COUNT(*) as cnt
               FROM generations WHERE user_id = ?
               GROUP BY platform ORDER BY cnt DESC""",
            (user_id,),
        ).fetchall()
        for r in rows:
            stats.platforms[r["platform"]] = r["cnt"]
        if stats.platforms:
            stats.most_used_platform = max(stats.platforms, key=stats.platforms.get)

        # Language breakdown
        rows = conn.execute(
            """SELECT language, COUNT(*) as cnt
               FROM generations WHERE user_id = ?
               GROUP BY language ORDER BY cnt DESC""",
            (user_id,),
        ).fetchall()
        for r in rows:
            stats.languages[r["language"]] = r["cnt"]

        # Recent activity
        now = time.time()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM generations WHERE user_id = ? AND created_at > ?",
            (user_id, now - 7 * 86400),
        ).fetchone()
        stats.last_7_days = row["cnt"] if row else 0

        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM generations WHERE user_id = ? AND created_at > ?",
            (user_id, now - 30 * 86400),
        ).fetchone()
        stats.last_30_days = row["cnt"] if row else 0

        # Top products
        rows = conn.execute(
            """SELECT product, COUNT(*) as cnt
               FROM generations WHERE user_id = ?
               GROUP BY product ORDER BY cnt DESC LIMIT 5""",
            (user_id,),
        ).fetchall()
        stats.top_products = [r["product"] for r in rows]

    return stats


@dataclass
class PlatformTrend:
    platform: str
    dates: list[str] = field(default_factory=list)
    counts: list[int] = field(default_factory=list)
    avg_scores: list[float] = field(default_factory=list)


def get_platform_trends(
    days: int = 30,
    user_id: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> list[PlatformTrend]:
    """Get generation trends by platform over time."""
    trends = {}

    with _get_db(db_path) as conn:
        params: list = []
        where = ""
        if user_id:
            where = "WHERE user_id = ?"
            params.append(user_id)

        cutoff = time.strftime(
            "%Y-%m-%d",
            time.localtime(time.time() - days * 86400),
        )
        if where:
            where += " AND date >= ?"
        else:
            where = "WHERE date >= ?"
        params.append(cutoff)

        rows = conn.execute(
            f"""SELECT date, platform, SUM(count) as cnt, AVG(avg_seo_score) as avg_score
                FROM daily_stats {where}
                GROUP BY date, platform
                ORDER BY date""",
            params,
        ).fetchall()

        for r in rows:
            platform = r["platform"]
            if platform not in trends:
                trends[platform] = PlatformTrend(platform=platform)
            trends[platform].dates.append(r["date"])
            trends[platform].counts.append(r["cnt"])
            trends[platform].avg_scores.append(r["avg_score"] or 0.0)

    return list(trends.values())


def get_global_stats(db_path: Optional[Path] = None) -> dict:
    """Get global platform statistics."""
    with _get_db(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) as cnt FROM generations").fetchone()["cnt"]
        platforms = conn.execute(
            """SELECT platform, COUNT(*) as cnt, AVG(seo_score) as avg_score
               FROM generations GROUP BY platform ORDER BY cnt DESC"""
        ).fetchall()
        languages = conn.execute(
            """SELECT language, COUNT(*) as cnt
               FROM generations GROUP BY language ORDER BY cnt DESC"""
        ).fetchall()
        recent = conn.execute(
            """SELECT COUNT(*) as cnt FROM generations
               WHERE created_at > ?""",
            (time.time() - 86400,),
        ).fetchone()

    return {
        "total_generations": total,
        "today": recent["cnt"],
        "platforms": {r["platform"]: {"count": r["cnt"], "avg_score": round(r["avg_score"] or 0, 1)} for r in platforms},
        "languages": {r["language"]: r["cnt"] for r in languages},
    }


def export_analytics_csv(
    user_id: Optional[int] = None,
    days: int = 30,
    db_path: Optional[Path] = None,
) -> str:
    """Export analytics data as CSV."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "User", "Platform", "Product", "Language",
                      "Chars", "SEO Score", "Validation", "Duration(ms)"])

    with _get_db(db_path) as conn:
        cutoff = time.time() - days * 86400
        params: list = [cutoff]
        where = "WHERE created_at > ?"
        if user_id:
            where += " AND user_id = ?"
            params.append(user_id)

        rows = conn.execute(
            f"""SELECT * FROM generations {where}
                ORDER BY created_at DESC""",
            params,
        ).fetchall()

        for r in rows:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["created_at"]))
            writer.writerow([
                ts, r["user_id"], r["platform"], r["product"],
                r["language"], r["char_count"], round(r["seo_score"], 1),
                round(r["validation_score"], 1), r["duration_ms"],
            ])

    return buf.getvalue()
