"""Tests for the bulk processing module."""
import pytest
import json
from app.bulk import (
    parse_csv,
    parse_json,
    parse_input,
    process_bulk,
    bulk_to_csv,
    bulk_to_json,
    BulkStatus,
    BulkResult,
    BulkItem,
)


# ── CSV Parsing ─────────────────────────────────────────────

class TestParseCSV:
    def test_basic_csv(self):
        csv_text = """product,platform,language
Wireless Headphones,amazon,English
Laptop Stand,shopee,中文"""
        records = parse_csv(csv_text)
        assert len(records) == 2
        assert records[0]["product"] == "Wireless Headphones"
        assert records[0]["platforms"] == ["amazon"]
        assert records[1]["language"] == "中文"

    def test_multiple_platforms(self):
        csv_text = "product,platform\nHeadphones,\"amazon,ebay,shopee\""
        records = parse_csv(csv_text)
        assert len(records) == 1
        assert len(records[0]["platforms"]) == 3

    def test_chinese_columns(self):
        csv_text = "产品,平台,语言\n蓝牙耳机,shopee,中文"
        records = parse_csv(csv_text)
        assert len(records) == 1
        assert records[0]["product"] == "蓝牙耳机"

    def test_with_instructions(self):
        csv_text = "product,platform,instructions\nHeadphones,amazon,Focus on bass quality"
        records = parse_csv(csv_text)
        assert records[0]["instructions"] == "Focus on bass quality"

    def test_empty_csv(self):
        records = parse_csv("product,platform\n")
        assert len(records) == 0

    def test_missing_product_skipped(self):
        csv_text = "product,platform\n,amazon\nValid Product,shopee"
        records = parse_csv(csv_text)
        assert len(records) == 1
        assert records[0]["product"] == "Valid Product"

    def test_default_platform(self):
        csv_text = "product\nHeadphones"
        records = parse_csv(csv_text)
        assert records[0]["platforms"] == ["amazon"]


# ── JSON Parsing ────────────────────────────────────────────

class TestParseJSON:
    def test_array_of_objects(self):
        json_text = json.dumps([
            {"product": "Headphones", "platform": "amazon"},
            {"product": "Laptop Stand", "platforms": ["shopee", "lazada"]},
        ])
        records = parse_json(json_text)
        assert len(records) == 2
        assert records[1]["platforms"] == ["shopee", "lazada"]

    def test_products_wrapper(self):
        json_text = json.dumps({
            "products": [
                {"product": "Phone Case", "platform": "tiktok"},
            ]
        })
        records = parse_json(json_text)
        assert len(records) == 1

    def test_string_array(self):
        json_text = json.dumps(["Headphones", "Laptop Stand", "Phone Case"])
        records = parse_json(json_text)
        assert len(records) == 3
        assert all(r["platforms"] == ["amazon"] for r in records)

    def test_chinese_product(self):
        json_text = json.dumps([{"产品": "蓝牙耳机", "platform": "shopee"}])
        records = parse_json(json_text)
        assert len(records) == 1

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json("not json")

    def test_invalid_structure_raises(self):
        with pytest.raises(ValueError):
            parse_json('"just a string"')


# ── Auto-detect Format ──────────────────────────────────────

class TestParseInput:
    def test_detects_json_array(self):
        records = parse_input('[{"product": "Test"}]')
        assert len(records) == 1

    def test_detects_json_object(self):
        records = parse_input('{"products": [{"product": "Test"}]}')
        assert len(records) == 1

    def test_detects_csv(self):
        records = parse_input("product,platform\nTest,amazon")
        assert len(records) == 1


# ── Bulk Processing ─────────────────────────────────────────

class TestProcessBulk:
    def test_successful_processing(self):
        records = [
            {"product": "Headphones", "platforms": ["amazon"], "language": "English"},
            {"product": "Laptop Stand", "platforms": ["shopee"], "language": "English"},
        ]

        def mock_generate(product, platform, language):
            return f"**Title** {product} for {platform}"

        result = process_bulk(records, mock_generate)
        assert isinstance(result, BulkResult)
        assert result.total_generated == 2
        assert result.total_failed == 0
        assert len(result.items) == 2
        assert result.items[0].status == BulkStatus.DONE

    def test_unknown_platform_fails(self):
        records = [{"product": "Test", "platforms": ["nonexistent"]}]

        def mock_generate(product, platform, language):
            return "listing"

        result = process_bulk(records, mock_generate)
        assert result.total_failed == 1

    def test_generation_error_handled(self):
        records = [{"product": "Test", "platforms": ["amazon"]}]

        def mock_generate(product, platform, language):
            raise RuntimeError("API error")

        result = process_bulk(records, mock_generate)
        assert result.total_failed == 1
        assert result.items[0].status == BulkStatus.FAILED

    def test_max_items_limit(self):
        records = [{"product": f"Product {i}", "platforms": ["amazon"]} for i in range(100)]

        def mock_generate(product, platform, language):
            return "listing"

        result = process_bulk(records, mock_generate, max_items=5)
        assert len(result.items) == 5

    def test_multi_platform_per_product(self):
        records = [{"product": "Headphones", "platforms": ["amazon", "ebay", "shopee"]}]

        def mock_generate(product, platform, language):
            return f"Listing for {platform}"

        result = process_bulk(records, mock_generate)
        assert result.total_generated == 3
        assert len(result.items[0].results) == 3

    def test_progress_callback(self):
        records = [{"product": f"P{i}", "platforms": ["amazon"]} for i in range(3)]
        progress_calls = []

        def mock_generate(product, platform, language):
            return "listing"

        def on_progress(current, total, name):
            progress_calls.append((current, total, name))

        process_bulk(records, mock_generate, on_progress)
        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3, "P0")

    def test_summary_output(self):
        records = [{"product": "Test", "platforms": ["amazon"]}]

        def mock_generate(product, platform, language):
            return "listing"

        result = process_bulk(records, mock_generate)
        summary = result.summary()
        assert "Bulk Processing Complete" in summary
        assert "Generated: 1" in summary

    def test_elapsed_time_tracked(self):
        records = [{"product": "Test", "platforms": ["amazon"]}]

        def mock_generate(product, platform, language):
            return "listing"

        result = process_bulk(records, mock_generate)
        assert result.elapsed_ms >= 0


# ── Export ──────────────────────────────────────────────────

class TestBulkExport:
    def _make_result(self):
        result = BulkResult(
            items=[
                BulkItem(
                    product="Headphones",
                    platforms=["amazon"],
                    status=BulkStatus.DONE,
                    results={"amazon": "**Title** Wireless Headphones"},
                ),
                BulkItem(
                    product="Stand",
                    platforms=["shopee"],
                    status=BulkStatus.FAILED,
                    errors={"shopee": "API timeout"},
                ),
            ],
            total_generated=1,
            total_failed=1,
        )
        return result

    def test_csv_export(self):
        csv_out = bulk_to_csv(self._make_result())
        assert "Headphones" in csv_out
        assert "amazon" in csv_out
        assert "Stand" in csv_out

    def test_json_export(self):
        json_out = bulk_to_json(self._make_result())
        data = json.loads(json_out)
        assert "summary" in data
        assert data["summary"]["generated"] == 1
        assert len(data["items"]) == 2

    def test_json_export_valid_json(self):
        json_out = bulk_to_json(self._make_result())
        # Should not raise
        json.loads(json_out)
