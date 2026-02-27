"""Tests for keywords module."""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault("BOT_TOKEN", "test-token-123")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.keywords import extract_keywords, keyword_density, compare_keywords


class TestExtractKeywords:
    def test_basic_extraction(self):
        text = "wireless bluetooth earbuds noise cancelling earbuds headphones wireless"
        kw = extract_keywords(text, top_n=5)
        assert "wireless" in kw
        assert "earbuds" in kw

    def test_filters_stop_words(self):
        text = "the best wireless earbuds for the price and quality"
        kw = extract_keywords(text, top_n=10)
        assert "the" not in kw
        assert "for" not in kw
        assert "and" not in kw

    def test_chinese_text(self):
        text = "蓝牙耳机 降噪 蓝牙耳机 无线 蓝牙耳机 运动"
        kw = extract_keywords(text, top_n=5)
        assert "蓝牙耳机" in kw

    def test_empty_text(self):
        assert extract_keywords("") == []

    def test_top_n_limit(self):
        text = " ".join(f"word{i}" for i in range(50))
        kw = extract_keywords(text, top_n=5)
        assert len(kw) <= 5

    def test_single_char_filtered(self):
        text = "a b c wireless earbuds d e"
        kw = extract_keywords(text, top_n=10)
        for k in kw:
            assert len(k) > 1


class TestKeywordDensity:
    def test_basic_density(self):
        text = "earbuds wireless earbuds bluetooth earbuds"
        density = keyword_density(text, "earbuds")
        assert density > 0
        # 3 out of 5 tokens = 60%
        assert abs(density - 60.0) < 1

    def test_zero_density(self):
        text = "wireless bluetooth headphones"
        assert keyword_density(text, "earbuds") == 0.0

    def test_empty_text(self):
        assert keyword_density("", "test") == 0.0

    def test_case_insensitive(self):
        text = "Earbuds EARBUDS earbuds"
        density = keyword_density(text, "EARBUDS")
        assert density == 100.0


class TestCompareKeywords:
    def test_compare_basic(self):
        a = "wireless bluetooth earbuds noise cancelling premium quality"
        b = "wireless headphones noise cancelling over ear comfortable"
        result = compare_keywords(a, b)
        assert "shared" in result
        assert "only_a" in result
        assert "only_b" in result
        assert "wireless" in result["shared"]

    def test_identical_texts(self):
        text = "wireless earbuds bluetooth"
        result = compare_keywords(text, text)
        assert len(result["only_a"]) == 0
        assert len(result["only_b"]) == 0
        assert len(result["shared"]) > 0

    def test_completely_different(self):
        a = "wireless earbuds bluetooth"
        b = "kitchen knife stainless steel"
        result = compare_keywords(a, b)
        assert len(result["shared"]) == 0

    def test_coverage_scores(self):
        a = "wireless earbuds bluetooth noise"
        b = "wireless earbuds premium quality"
        result = compare_keywords(a, b)
        assert 0 <= result["coverage_a"] <= 1
        assert 0 <= result["coverage_b"] <= 1
