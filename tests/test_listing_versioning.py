"""Tests for Listing Versioning."""
import pytest
import tempfile
import os
from app.listing_versioning import (
    ListingVersionManager,
    Version, VersionComparison, VersionTimeline, FieldDiff,
    ChangeType, FieldName,
    _parse_version, _bump_version, _hash_data, _compute_text_diff,
    _compute_field_diff, _determine_severity,
)


class TestVersionParsing:
    def test_parse_simple_version(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_parse_two_part_version(self):
        assert _parse_version("2.5") == (2, 5, 0)

    def test_parse_single_part(self):
        assert _parse_version("3") == (3, 0, 0)

    def test_parse_empty(self):
        assert _parse_version("") == (0, 0, 0)


class TestVersionBumping:
    def test_bump_major(self):
        assert _bump_version("1.2.3", "major") == "2.0.0"

    def test_bump_minor(self):
        assert _bump_version("1.2.3", "minor") == "1.3.0"

    def test_bump_patch(self):
        assert _bump_version("1.2.3", "patch") == "1.2.4"

    def test_bump_from_zero(self):
        assert _bump_version("0.0.0", "minor") == "0.1.0"


class TestHashData:
    def test_hash_same_data(self):
        data1 = {"title": "Test", "price": 10}
        data2 = {"title": "Test", "price": 10}
        assert _hash_data(data1) == _hash_data(data2)

    def test_hash_different_data(self):
        data1 = {"title": "Test A"}
        data2 = {"title": "Test B"}
        assert _hash_data(data1) != _hash_data(data2)

    def test_hash_order_independent(self):
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        assert _hash_data(data1) == _hash_data(data2)


class TestTextDiff:
    def test_identical_text(self):
        diff, ratio = _compute_text_diff("hello", "hello")
        assert ratio == 1.0
        assert len(diff) == 0

    def test_completely_different(self):
        diff, ratio = _compute_text_diff("abc", "xyz")
        assert ratio < 0.3

    def test_similar_text(self):
        diff, ratio = _compute_text_diff("hello world", "hello there")
        assert 0.3 < ratio < 0.9

    def test_none_values(self):
        diff, ratio = _compute_text_diff(None, "text")
        assert ratio < 1.0


class TestFieldDiff:
    def test_field_added(self):
        diff = _compute_field_diff("title", None, "New Title")
        assert diff.change_type == "added"
        assert diff.similarity == 0.0

    def test_field_removed(self):
        diff = _compute_field_diff("title", "Old Title", None)
        assert diff.change_type == "removed"
        assert diff.similarity == 0.0

    def test_field_unchanged(self):
        diff = _compute_field_diff("title", "Same", "Same")
        assert diff.change_type == "unchanged"
        assert diff.similarity == 1.0

    def test_field_modified(self):
        diff = _compute_field_diff("title", "Old Title", "New Title")
        assert diff.change_type == "modified"
        assert 0.0 < diff.similarity < 1.0

    def test_complex_field(self):
        old_list = ["a", "b", "c"]
        new_list = ["a", "b", "d"]
        diff = _compute_field_diff("items", old_list, new_list)
        assert diff.change_type == "modified"


class TestSeverityDetermination:
    def test_major_severity(self):
        diffs = [
            FieldDiff("title", "Old", "New", "modified", [], 0.5)
        ]
        severity = _determine_severity(diffs)
        assert severity == "major"

    def test_minor_severity(self):
        diffs = [
            FieldDiff("description", "Old", "New", "modified", [], 0.7)
        ]
        severity = _determine_severity(diffs)
        assert severity == "minor"

    def test_patch_severity(self):
        diffs = [
            FieldDiff("price", "10", "11", "modified", [], 0.9)
        ]
        severity = _determine_severity(diffs)
        assert severity == "patch"

    def test_unchanged_severity(self):
        diffs = [
            FieldDiff("title", "Same", "Same", "unchanged", [], 1.0)
        ]
        severity = _determine_severity(diffs)
        assert severity == "patch"


class TestVersionManager:
    def test_save_first_version(self):
        mgr = ListingVersionManager(db_path=None)  # In-memory
        data = {"title": "Test Product", "price": 10.0}
        v = mgr.save_version("PROD1", data, "Initial version")
        assert v.version_id == "1.0.0"
        assert v.change_type == "major"

    def test_save_incremental_version(self):
        mgr = ListingVersionManager()
        data1 = {"title": "Product", "price": 10}
        v1 = mgr.save_version("PROD1", data1, "First")

        data2 = {"title": "Product Updated", "price": 10}
        v2 = mgr.save_version("PROD1", data2, "Title change")
        assert v2.version_id == "2.0.0"  # Title change = major
        assert v2.parent_version == "1.0.0"

    def test_auto_detect_change_type(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "A", "price": 10})

        # Major change (title)
        v2 = mgr.save_version("PROD1", {"title": "B", "price": 10})
        assert v2.change_type == "major"

        # Patch change (price)
        v3 = mgr.save_version("PROD1", {"title": "B", "price": 11})
        assert v3.change_type == "patch"

    def test_no_change_returns_current(self):
        mgr = ListingVersionManager()
        data = {"title": "Same", "price": 10}
        v1 = mgr.save_version("PROD1", data)
        v2 = mgr.save_version("PROD1", data)  # Same data
        assert v1.version_id == v2.version_id

    def test_get_latest(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "V1"})
        mgr.save_version("PROD1", {"title": "V2"})
        mgr.save_version("PROD1", {"title": "V3"})
        latest = mgr.get_latest("PROD1")
        assert latest.version_id == "3.0.0"

    def test_get_specific_version(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "V1"})
        mgr.save_version("PROD1", {"title": "V2"})
        v1 = mgr.get_version("PROD1", "1.0.0")
        assert v1 is not None
        assert v1.data["title"] == "V1"

    def test_version_not_found(self):
        mgr = ListingVersionManager()
        v = mgr.get_version("NONEXISTENT", "1.0.0")
        assert v is None


class TestVersionTimeline:
    def test_get_timeline(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "V1"})
        mgr.save_version("PROD1", {"title": "V2"})
        mgr.save_version("PROD1", {"title": "V3"})
        timeline = mgr.get_timeline("PROD1")
        assert timeline.total_versions == 3
        assert timeline.current_version == "3.0.0"

    def test_timeline_branch_filtering(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "Main"}, branch="main")
        mgr.create_branch("PROD1", "test", from_branch="main")
        timeline = mgr.get_timeline("PROD1", branch="main")
        # Should only show main branch versions
        assert all(v.branch == "main" for v in timeline.versions)

    def test_timeline_limit(self):
        mgr = ListingVersionManager()
        for i in range(20):
            mgr.save_version("PROD1", {"title": f"V{i}"})
        timeline = mgr.get_timeline("PROD1", limit=10)
        assert len(timeline.versions) == 10


class TestVersionComparison:
    def test_compare_versions(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "Old", "price": 10})
        mgr.save_version("PROD1", {"title": "New", "price": 15})
        comparison = mgr.compare("PROD1", "1.0.0", "2.0.0")
        assert comparison is not None
        assert comparison.changed_fields > 0
        assert comparison.overall_similarity < 1.0

    def test_compare_identical(self):
        mgr = ListingVersionManager()
        data = {"title": "Same", "price": 10}
        mgr.save_version("PROD1", data)
        mgr.save_version("PROD1", data, change_type="patch")  # Force new version
        comparison = mgr.compare("PROD1", "1.0.0", "1.0.1")
        assert comparison.overall_similarity == 1.0
        assert comparison.changed_fields == 0

    def test_comparison_severity(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "A", "price": 10})
        mgr.save_version("PROD1", {"title": "B", "price": 10})
        comparison = mgr.compare("PROD1", "1.0.0", "2.0.0")
        assert comparison.change_severity in ["major", "minor", "patch"]

    def test_compare_nonexistent(self):
        mgr = ListingVersionManager()
        comparison = mgr.compare("PROD1", "1.0.0", "2.0.0")
        assert comparison is None


class TestRollback:
    def test_rollback_to_previous(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "V1", "price": 10})
        mgr.save_version("PROD1", {"title": "V2", "price": 20})
        mgr.save_version("PROD1", {"title": "V3", "price": 30})

        rollback = mgr.rollback("PROD1", "1.0.0")
        assert rollback is not None
        assert rollback.data["title"] == "V1"
        assert rollback.data["price"] == 10
        assert "Rollback" in rollback.change_summary

    def test_rollback_nonexistent(self):
        mgr = ListingVersionManager()
        rollback = mgr.rollback("PROD1", "9.9.9")
        assert rollback is None


class TestBranching:
    def test_create_branch(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "Main"}, branch="main")
        branch = mgr.create_branch("PROD1", "feature-1", from_branch="main")
        assert branch is not None
        assert branch.branch == "feature-1"

    def test_branch_from_nonexistent(self):
        mgr = ListingVersionManager()
        branch = mgr.create_branch("PROD1", "test", from_branch="main")
        assert branch is None

    def test_merge_branch(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "Main"}, branch="main")
        mgr.create_branch("PROD1", "feature", from_branch="main")
        mgr.save_version("PROD1", {"title": "Feature Update"}, branch="feature")

        merged = mgr.merge_branch("PROD1", "feature", target_branch="main")
        assert merged is not None
        assert merged.branch == "main"
        assert "Merge" in merged.change_summary

    def test_get_branches(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "Main"}, branch="main")
        mgr.create_branch("PROD1", "dev", from_branch="main")
        mgr.create_branch("PROD1", "staging", from_branch="main")
        branches = mgr.get_branches("PROD1")
        assert "main" in branches
        assert "dev" in branches
        assert "staging" in branches


class TestAutoVersioning:
    def test_auto_version_above_threshold(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "Original", "description": "Old"})
        v = mgr.auto_version("PROD1", {"title": "Completely New", "description": "New"},
                              threshold=0.05)
        assert v is not None
        assert v.version_id == "2.0.0"

    def test_auto_version_below_threshold(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "Original", "price": 10.0})
        v = mgr.auto_version("PROD1", {"title": "Original", "price": 10.01},
                              threshold=0.05)
        assert v is None  # Too small change

    def test_auto_version_summary(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "A", "price": 10, "description": "D"})
        v = mgr.auto_version("PROD1", {"title": "B", "price": 11, "description": "E"})
        assert "Updated:" in v.change_summary
        # Should list changed fields
        assert any(field in v.change_summary.lower() for field in ["title", "price", "description"])


class TestExport:
    def test_export_timeline_json(self):
        mgr = ListingVersionManager()
        mgr.save_version("PROD1", {"title": "V1"})
        mgr.save_version("PROD1", {"title": "V2"})
        json_str = mgr.export_timeline_json("PROD1")
        assert "listing_id" in json_str
        assert "PROD1" in json_str
        assert "versions" in json_str

    def test_export_empty_timeline(self):
        mgr = ListingVersionManager()
        json_str = mgr.export_timeline_json("NONEXISTENT")
        assert "NONEXISTENT" in json_str
        assert "total_versions" in json_str


class TestPersistence:
    def test_sqlite_persistence(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            mgr = ListingVersionManager(db_path=db_path)
            mgr.save_version("PROD1", {"title": "Test"})

            # Create new manager instance
            mgr2 = ListingVersionManager(db_path=db_path)
            latest = mgr2.get_latest("PROD1")
            assert latest is not None
            assert latest.data["title"] == "Test"
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_concurrent_versions(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            mgr = ListingVersionManager(db_path=db_path)
            mgr.save_version("PROD1", {"title": "A"})
            mgr.save_version("PROD2", {"title": "B"})
            mgr.save_version("PROD1", {"title": "A2"})

            timeline1 = mgr.get_timeline("PROD1")
            timeline2 = mgr.get_timeline("PROD2")
            assert timeline1.total_versions == 2
            assert timeline2.total_versions == 1
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestEdgeCases:
    def test_empty_data(self):
        mgr = ListingVersionManager()
        v = mgr.save_version("PROD1", {})
        assert v.version_id == "1.0.0"

    def test_large_data(self):
        mgr = ListingVersionManager()
        large_data = {"title": "X" * 10000, "description": "Y" * 50000}
        v = mgr.save_version("PROD1", large_data)
        assert v is not None

    def test_special_characters_in_data(self):
        mgr = ListingVersionManager()
        data = {"title": "Test™️ Product® with 中文 and émojis 🎉"}
        v = mgr.save_version("PROD1", data)
        retrieved = mgr.get_version("PROD1", v.version_id)
        assert retrieved.data["title"] == data["title"]

    def test_unicode_listing_id(self):
        mgr = ListingVersionManager()
        v = mgr.save_version("产品-123", {"title": "测试"})
        assert v.listing_id == "产品-123"
