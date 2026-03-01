"""Listing Versioning — version control for listing changes with diff, rollback,
branching, and change history tracking.

Features:
- Semantic versioning for listings (major.minor.patch)
- Full change history with diff generation
- Rollback to any previous version
- Version branching for A/B test variants
- Change attribution and annotation
- Field-level diff (title, description, price, images, etc.)
- Version comparison across any two versions
- Auto-versioning on significant changes
- Export version timeline
- SQLite storage
"""

from __future__ import annotations

import sqlite3
import json
import hashlib
import difflib
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class ChangeType(str, Enum):
    MAJOR = "major"       # Breaking changes (new title, category change)
    MINOR = "minor"       # Feature additions (new bullet, image add)
    PATCH = "patch"       # Small fixes (typo, price tweak)
    ROLLBACK = "rollback" # Reverted to previous version


class FieldName(str, Enum):
    TITLE = "title"
    DESCRIPTION = "description"
    BULLETS = "bullets"
    PRICE = "price"
    IMAGES = "images"
    KEYWORDS = "keywords"
    CATEGORY = "category"
    BRAND = "brand"
    SKU = "sku"
    TAGS = "tags"
    VARIANTS = "variants"
    CUSTOM = "custom"


# Which field changes count as major/minor/patch
FIELD_CHANGE_SEVERITY: dict[str, str] = {
    "title": "major",
    "category": "major",
    "brand": "major",
    "description": "minor",
    "bullets": "minor",
    "images": "minor",
    "keywords": "minor",
    "variants": "minor",
    "price": "patch",
    "sku": "patch",
    "tags": "patch",
    "custom": "patch",
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FieldDiff:
    """Diff for a single field."""
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_type: str = "modified"  # added, removed, modified, unchanged
    diff_lines: list[str] = field(default_factory=list)
    similarity: float = 0.0       # 0-1, how similar old and new are

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_type": self.change_type,
            "diff_lines": self.diff_lines,
            "similarity": round(self.similarity, 3),
        }


@dataclass
class Version:
    """A listing version snapshot."""
    version_id: str           # Semantic version "1.2.3"
    listing_id: str
    data: dict                # Full listing data at this version
    change_type: str = "patch"
    change_summary: str = ""
    author: str = "system"
    branch: str = "main"
    parent_version: str = ""
    content_hash: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.content_hash:
            self.content_hash = _hash_data(self.data)

    def to_dict(self) -> dict:
        return {
            "version_id": self.version_id,
            "listing_id": self.listing_id,
            "data": self.data,
            "change_type": self.change_type,
            "change_summary": self.change_summary,
            "author": self.author,
            "branch": self.branch,
            "parent_version": self.parent_version,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
        }


@dataclass
class VersionComparison:
    """Comparison between two versions."""
    version_a: str
    version_b: str
    listing_id: str
    field_diffs: list[FieldDiff] = field(default_factory=list)
    overall_similarity: float = 0.0
    change_severity: str = "patch"
    changed_fields: int = 0
    total_fields: int = 0

    def to_dict(self) -> dict:
        return {
            "version_a": self.version_a,
            "version_b": self.version_b,
            "listing_id": self.listing_id,
            "field_diffs": [d.to_dict() for d in self.field_diffs],
            "overall_similarity": round(self.overall_similarity, 3),
            "change_severity": self.change_severity,
            "changed_fields": self.changed_fields,
            "total_fields": self.total_fields,
        }

    def summary(self) -> str:
        lines = [
            f"═══ Version Comparison: {self.version_a} → {self.version_b} ═══",
            f"Overall similarity: {self.overall_similarity:.0%}",
            f"Changed fields: {self.changed_fields}/{self.total_fields}",
            f"Severity: {self.change_severity}",
        ]
        for d in self.field_diffs:
            if d.change_type != "unchanged":
                lines.append(f"  {d.change_type.upper()}: {d.field} "
                            f"(similarity: {d.similarity:.0%})")
        return "\n".join(lines)


@dataclass
class VersionTimeline:
    """Timeline of all versions for a listing."""
    listing_id: str
    versions: list[Version] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)
    total_versions: int = 0
    current_version: str = ""

    def summary(self) -> str:
        lines = [
            f"═══ Version Timeline: {self.listing_id} ═══",
            f"Total versions: {self.total_versions}",
            f"Current: {self.current_version}",
            f"Branches: {', '.join(self.branches)}",
        ]
        for v in self.versions[-10:]:  # Last 10
            lines.append(f"  {v.version_id} [{v.change_type}] {v.change_summary[:60]} "
                        f"({v.created_at[:10]}) @{v.author}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_data(data: dict) -> str:
    """Generate content hash for data."""
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def _parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse semantic version string."""
    parts = version_str.split(".")
    return (
        int(parts[0]) if len(parts) > 0 else 0,
        int(parts[1]) if len(parts) > 1 else 0,
        int(parts[2]) if len(parts) > 2 else 0,
    )


def _bump_version(current: str, change_type: str) -> str:
    """Bump version based on change type."""
    major, minor, patch = _parse_version(current)
    if change_type == ChangeType.MAJOR.value:
        return f"{major + 1}.0.0"
    elif change_type == ChangeType.MINOR.value:
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def _compute_text_diff(old: str, new: str) -> tuple[list[str], float]:
    """Compute unified diff and similarity ratio."""
    if old is None:
        old = ""
    if new is None:
        new = ""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    ratio = difflib.SequenceMatcher(None, old, new).ratio()
    return diff, ratio


def _compute_field_diff(field_name: str, old_val, new_val) -> FieldDiff:
    """Compute diff for a single field."""
    old_str = json.dumps(old_val, ensure_ascii=False) if not isinstance(old_val, str) else (old_val or "")
    new_str = json.dumps(new_val, ensure_ascii=False) if not isinstance(new_val, str) else (new_val or "")

    if old_val is None and new_val is not None:
        return FieldDiff(
            field=field_name,
            old_value=None,
            new_value=new_str,
            change_type="added",
            similarity=0.0,
        )
    elif old_val is not None and new_val is None:
        return FieldDiff(
            field=field_name,
            old_value=old_str,
            new_value=None,
            change_type="removed",
            similarity=0.0,
        )
    elif old_str == new_str:
        return FieldDiff(
            field=field_name,
            old_value=old_str,
            new_value=new_str,
            change_type="unchanged",
            similarity=1.0,
        )
    else:
        diff_lines, similarity = _compute_text_diff(old_str, new_str)
        return FieldDiff(
            field=field_name,
            old_value=old_str,
            new_value=new_str,
            change_type="modified",
            diff_lines=diff_lines[:50],  # Cap diff lines
            similarity=similarity,
        )


def _determine_severity(field_diffs: list[FieldDiff]) -> str:
    """Determine overall change severity from field diffs."""
    max_severity = "patch"
    severity_order = {"major": 3, "minor": 2, "patch": 1}

    for fd in field_diffs:
        if fd.change_type == "unchanged":
            continue
        field_severity = FIELD_CHANGE_SEVERITY.get(fd.field, "patch")
        if severity_order.get(field_severity, 0) > severity_order.get(max_severity, 0):
            max_severity = field_severity
    return max_severity


# ---------------------------------------------------------------------------
# Core Engine
# ---------------------------------------------------------------------------

class ListingVersionManager:
    """Manage listing versions with diff, rollback, and branching."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self._memory: dict[str, list[Version]] = {}  # In-memory fallback
        if db_path:
            self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listing_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                data_json TEXT NOT NULL,
                change_type TEXT DEFAULT 'patch',
                change_summary TEXT DEFAULT '',
                author TEXT DEFAULT 'system',
                branch TEXT DEFAULT 'main',
                parent_version TEXT DEFAULT '',
                content_hash TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(listing_id, version_id, branch)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_version_listing
            ON listing_versions(listing_id, branch)
        """)
        conn.commit()
        conn.close()

    def save_version(
        self,
        listing_id: str,
        data: dict,
        change_summary: str = "",
        author: str = "system",
        branch: str = "main",
        change_type: Optional[str] = None,
    ) -> Version:
        """Save a new version of a listing. Auto-detects change type if not specified."""
        # Get current version
        current = self.get_latest(listing_id, branch)

        if current:
            # Auto-detect change type
            if not change_type:
                comparison = self._compare_data(current.data, data)
                change_type = _determine_severity(comparison)
            version_id = _bump_version(current.version_id, change_type)
            parent = current.version_id

            # Check if content actually changed
            new_hash = _hash_data(data)
            if new_hash == current.content_hash:
                return current  # No change, return existing
        else:
            version_id = "1.0.0"
            change_type = change_type or "major"
            parent = ""

        version = Version(
            version_id=version_id,
            listing_id=listing_id,
            data=data,
            change_type=change_type,
            change_summary=change_summary,
            author=author,
            branch=branch,
            parent_version=parent,
        )

        self._persist_version(version)
        return version

    def get_latest(self, listing_id: str, branch: str = "main") -> Optional[Version]:
        """Get the latest version of a listing."""
        if self.db_path:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT version_id, listing_id, data_json, change_type, change_summary, "
                "author, branch, parent_version, content_hash, created_at "
                "FROM listing_versions WHERE listing_id = ? AND branch = ? "
                "ORDER BY id DESC LIMIT 1",
                (listing_id, branch),
            ).fetchone()
            conn.close()
            if row:
                return Version(
                    version_id=row[0], listing_id=row[1],
                    data=json.loads(row[2]), change_type=row[3],
                    change_summary=row[4], author=row[5],
                    branch=row[6], parent_version=row[7],
                    content_hash=row[8], created_at=row[9],
                )
            return None
        else:
            key = f"{listing_id}:{branch}"
            versions = self._memory.get(key, [])
            return versions[-1] if versions else None

    def get_version(self, listing_id: str, version_id: str,
                    branch: str = "main") -> Optional[Version]:
        """Get a specific version."""
        if self.db_path:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT version_id, listing_id, data_json, change_type, change_summary, "
                "author, branch, parent_version, content_hash, created_at "
                "FROM listing_versions WHERE listing_id = ? AND version_id = ? AND branch = ?",
                (listing_id, version_id, branch),
            ).fetchone()
            conn.close()
            if row:
                return Version(
                    version_id=row[0], listing_id=row[1],
                    data=json.loads(row[2]), change_type=row[3],
                    change_summary=row[4], author=row[5],
                    branch=row[6], parent_version=row[7],
                    content_hash=row[8], created_at=row[9],
                )
            return None
        else:
            key = f"{listing_id}:{branch}"
            for v in self._memory.get(key, []):
                if v.version_id == version_id:
                    return v
            return None

    def get_timeline(self, listing_id: str, branch: Optional[str] = None,
                     limit: int = 50) -> VersionTimeline:
        """Get version timeline for a listing."""
        versions = []
        branches_found = set()

        if self.db_path:
            conn = sqlite3.connect(self.db_path)
            if branch:
                rows = conn.execute(
                    "SELECT version_id, listing_id, data_json, change_type, change_summary, "
                    "author, branch, parent_version, content_hash, created_at "
                    "FROM listing_versions WHERE listing_id = ? AND branch = ? "
                    "ORDER BY id DESC LIMIT ?",
                    (listing_id, branch, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT version_id, listing_id, data_json, change_type, change_summary, "
                    "author, branch, parent_version, content_hash, created_at "
                    "FROM listing_versions WHERE listing_id = ? "
                    "ORDER BY id DESC LIMIT ?",
                    (listing_id, limit),
                ).fetchall()
            conn.close()

            for row in rows:
                v = Version(
                    version_id=row[0], listing_id=row[1],
                    data=json.loads(row[2]), change_type=row[3],
                    change_summary=row[4], author=row[5],
                    branch=row[6], parent_version=row[7],
                    content_hash=row[8], created_at=row[9],
                )
                versions.append(v)
                branches_found.add(row[6])
        else:
            for key, vers in self._memory.items():
                if key.startswith(f"{listing_id}:"):
                    br = key.split(":")[1]
                    if branch and br != branch:
                        continue
                    versions.extend(vers[-limit:])
                    branches_found.add(br)

        versions.reverse()  # Chronological order
        current = versions[-1].version_id if versions else ""

        return VersionTimeline(
            listing_id=listing_id,
            versions=versions,
            branches=sorted(branches_found),
            total_versions=len(versions),
            current_version=current,
        )

    def compare(self, listing_id: str, version_a: str, version_b: str,
                branch: str = "main") -> Optional[VersionComparison]:
        """Compare two versions of a listing."""
        va = self.get_version(listing_id, version_a, branch)
        vb = self.get_version(listing_id, version_b, branch)
        if not va or not vb:
            return None

        field_diffs = self._compare_data(va.data, vb.data)
        changed = sum(1 for d in field_diffs if d.change_type != "unchanged")
        total = len(field_diffs)
        severity = _determine_severity(field_diffs)

        # Overall similarity
        similarities = [d.similarity for d in field_diffs]
        overall = sum(similarities) / len(similarities) if similarities else 1.0

        return VersionComparison(
            version_a=version_a,
            version_b=version_b,
            listing_id=listing_id,
            field_diffs=field_diffs,
            overall_similarity=overall,
            change_severity=severity,
            changed_fields=changed,
            total_fields=total,
        )

    def rollback(self, listing_id: str, target_version: str,
                 branch: str = "main", author: str = "system") -> Optional[Version]:
        """Rollback to a previous version."""
        target = self.get_version(listing_id, target_version, branch)
        if not target:
            return None

        return self.save_version(
            listing_id=listing_id,
            data=target.data,
            change_summary=f"Rollback to v{target_version}",
            author=author,
            branch=branch,
            change_type=ChangeType.ROLLBACK.value,
        )

    def create_branch(self, listing_id: str, branch_name: str,
                      from_branch: str = "main",
                      author: str = "system") -> Optional[Version]:
        """Create a new branch from current version."""
        current = self.get_latest(listing_id, from_branch)
        if not current:
            return None

        return self.save_version(
            listing_id=listing_id,
            data=current.data,
            change_summary=f"Branch '{branch_name}' from {from_branch} v{current.version_id}",
            author=author,
            branch=branch_name,
            change_type="patch",
        )

    def merge_branch(self, listing_id: str, source_branch: str,
                     target_branch: str = "main",
                     author: str = "system") -> Optional[Version]:
        """Merge a branch into target branch."""
        source = self.get_latest(listing_id, source_branch)
        if not source:
            return None

        return self.save_version(
            listing_id=listing_id,
            data=source.data,
            change_summary=f"Merge '{source_branch}' v{source.version_id} into {target_branch}",
            author=author,
            branch=target_branch,
            change_type="minor",
        )

    def get_branches(self, listing_id: str) -> list[str]:
        """Get all branches for a listing."""
        if self.db_path:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT DISTINCT branch FROM listing_versions WHERE listing_id = ?",
                (listing_id,),
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        else:
            branches = []
            for key in self._memory:
                if key.startswith(f"{listing_id}:"):
                    branches.append(key.split(":")[1])
            return branches

    def auto_version(
        self,
        listing_id: str,
        new_data: dict,
        branch: str = "main",
        author: str = "system",
        threshold: float = 0.05,
    ) -> Optional[Version]:
        """Auto-create version only if changes exceed threshold."""
        current = self.get_latest(listing_id, branch)
        if not current:
            return self.save_version(listing_id, new_data, "Initial version", author, branch)

        # Compare
        diffs = self._compare_data(current.data, new_data)
        changed = [d for d in diffs if d.change_type != "unchanged"]
        if not changed:
            return None  # No changes

        avg_sim = sum(d.similarity for d in diffs) / len(diffs) if diffs else 1.0
        change_ratio = 1.0 - avg_sim

        if change_ratio < threshold:
            return None  # Below threshold

        # Auto-generate summary
        changed_fields = [d.field for d in changed]
        summary = f"Updated: {', '.join(changed_fields[:5])}"
        if len(changed_fields) > 5:
            summary += f" +{len(changed_fields) - 5} more"

        return self.save_version(
            listing_id=listing_id,
            data=new_data,
            change_summary=summary,
            author=author,
            branch=branch,
        )

    def export_timeline_json(self, listing_id: str,
                              branch: Optional[str] = None) -> str:
        """Export version timeline as JSON."""
        timeline = self.get_timeline(listing_id, branch)
        data = {
            "listing_id": timeline.listing_id,
            "current_version": timeline.current_version,
            "total_versions": timeline.total_versions,
            "branches": timeline.branches,
            "versions": [
                {
                    "version_id": v.version_id,
                    "change_type": v.change_type,
                    "change_summary": v.change_summary,
                    "author": v.author,
                    "branch": v.branch,
                    "created_at": v.created_at,
                    "content_hash": v.content_hash,
                }
                for v in timeline.versions
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    # ── Internal methods ─────────────────────────────────

    def _compare_data(self, old_data: dict, new_data: dict) -> list[FieldDiff]:
        """Compare two data dicts field by field."""
        all_keys = set(list(old_data.keys()) + list(new_data.keys()))
        diffs = []
        for key in sorted(all_keys):
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            diff = _compute_field_diff(key, old_val, new_val)
            diffs.append(diff)
        return diffs

    def _persist_version(self, version: Version):
        """Persist version to storage."""
        if self.db_path:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR REPLACE INTO listing_versions "
                "(version_id, listing_id, data_json, change_type, change_summary, "
                "author, branch, parent_version, content_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (version.version_id, version.listing_id,
                 json.dumps(version.data, ensure_ascii=False),
                 version.change_type, version.change_summary,
                 version.author, version.branch, version.parent_version,
                 version.content_hash, version.created_at),
            )
            conn.commit()
            conn.close()
        else:
            key = f"{version.listing_id}:{version.branch}"
            if key not in self._memory:
                self._memory[key] = []
            self._memory[key].append(version)
