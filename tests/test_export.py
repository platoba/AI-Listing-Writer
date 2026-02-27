"""Tests for export module."""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.export import export_csv, export_json, export_txt, export_html, export_records


def _make_records(n=3):
    return [
        {
            "platform": f"platform_{i}",
            "product": f"product_{i}",
            "preview": f"Preview text for item {i}",
            "ts": int(time.time()) - i * 3600,
        }
        for i in range(n)
    ]


class TestExportCSV:
    def test_csv_basic(self):
        records = _make_records(2)
        result = export_csv(records)
        assert "Platform,Product,Generated At,Preview" in result
        assert "platform_0" in result
        assert "platform_1" in result

    def test_csv_empty(self):
        assert export_csv([]) == ""

    def test_csv_special_chars(self):
        records = [{"platform": "test", "product": 'has "quotes"', "preview": "a,b,c", "ts": 0}]
        result = export_csv(records)
        assert "test" in result


class TestExportJSON:
    def test_json_valid(self):
        records = _make_records(2)
        result = export_json(records)
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["platform"] == "platform_0"

    def test_json_empty(self):
        result = export_json([])
        assert json.loads(result) == []

    def test_json_compact(self):
        records = _make_records(1)
        result = export_json(records, pretty=False)
        assert "\n" not in result


class TestExportTXT:
    def test_txt_basic(self):
        records = _make_records(2)
        result = export_txt(records)
        assert "AI Listing Writer" in result
        assert "#1" in result
        assert "#2" in result

    def test_txt_empty(self):
        assert "No records" in export_txt([])


class TestExportHTML:
    def test_html_table(self):
        records = _make_records(2)
        result = export_html(records)
        assert "<table" in result
        assert "platform_0" in result
        assert "</table>" in result

    def test_html_empty(self):
        assert "<p>" in export_html([])

    def test_html_escapes(self):
        records = [{"platform": "<script>", "product": "a&b", "preview": "x>y", "ts": 0}]
        result = export_html(records)
        assert "&lt;script&gt;" in result
        assert "a&amp;b" in result


class TestExportRecords:
    def test_supported_formats(self):
        records = _make_records(1)
        for fmt in ["csv", "json", "txt", "html"]:
            result = export_records(records, fmt)
            assert result is not None
            assert len(result) > 0

    def test_unknown_format(self):
        assert export_records(_make_records(1), "xml") is None

    def test_case_insensitive(self):
        records = _make_records(1)
        assert export_records(records, "CSV") is not None
        assert export_records(records, "Json") is not None
