"""Tests for the multi-language translator module."""
import pytest
from unittest.mock import patch
from app.translator import (
    LOCALES,
    LocaleProfile,
    TranslationResult,
    translate_listing,
    list_locales,
    batch_translate,
)


# ── Locale Registry ─────────────────────────────────────────

class TestLocaleRegistry:
    def test_major_locales_present(self):
        expected = ["en-US", "en-UK", "zh-CN", "zh-TW", "ja-JP", "ko-KR",
                     "de-DE", "fr-FR", "es-ES", "pt-BR", "ar-AE", "th-TH",
                     "vi-VN", "id-ID", "ms-MY"]
        for code in expected:
            assert code in LOCALES, f"Missing locale: {code}"

    def test_locale_has_required_fields(self):
        for code, profile in LOCALES.items():
            assert isinstance(profile, LocaleProfile)
            assert profile.code == code
            assert profile.name != ""
            assert profile.currency != ""
            assert profile.platform_notes != ""
            assert profile.search_behavior != ""

    def test_currency_symbols(self):
        assert LOCALES["en-US"].currency == "$"
        assert LOCALES["ja-JP"].currency == "¥"
        assert LOCALES["de-DE"].currency == "€"
        assert LOCALES["pt-BR"].currency == "R$"
        assert LOCALES["th-TH"].currency == "฿"

    def test_locale_count(self):
        assert len(LOCALES) >= 15


# ── TranslationResult ──────────────────────────────────────

class TestTranslationResult:
    def test_summary_output(self):
        result = TranslationResult(
            source_locale="en-US",
            target_locale="ja-JP",
            original="Original",
            translated="翻訳",
            adaptations=["Adapted honorific language", "Changed units to metric"],
            seo_changes=["Added katakana keywords"],
        )
        summary = result.summary()
        assert "en-US" in summary
        assert "ja-JP" in summary
        assert "Adaptations: 2" in summary

    def test_empty_adaptations(self):
        result = TranslationResult(
            source_locale="en-US",
            target_locale="fr-FR",
            original="test",
            translated="test",
        )
        summary = result.summary()
        assert "Adaptations: 0" in summary


# ── Translation with Mock AI ───────────────────────────────

class TestTranslateListing:
    @patch("app.translator.call_ai")
    def test_translate_to_japanese(self, mock_ai):
        mock_ai.return_value = """**タイトル** プレミアムワイヤレスヘッドフォン
**説明** 高品質のオーディオ体験

ADAPTATIONS:
- Added 敬語 (polite language) throughout
- Changed inches to centimeters

SEO_CHANGES:
- Added カタカナ brand keywords"""

        result = translate_listing(
            "**Title** Premium Headphones\n**Description** Quality audio",
            "ja-JP",
            "en-US",
            "amazon",
        )
        assert isinstance(result, TranslationResult)
        assert result.target_locale == "ja-JP"
        assert len(result.adaptations) == 2
        assert len(result.seo_changes) == 1
        assert "タイトル" in result.translated

    @patch("app.translator.call_ai")
    def test_translate_to_german(self, mock_ai):
        mock_ai.return_value = """**Titel** Premium-Kopfhörer
**Beschreibung** Hochwertige Audioqualität

ADAPTATIONS:
- Formal tone (Sie form)

SEO_CHANGES:
- German compound nouns added"""

        result = translate_listing(
            "**Title** Headphones", "de-DE",
        )
        assert result.target_locale == "de-DE"
        assert len(result.adaptations) >= 1

    @patch("app.translator.call_ai")
    def test_translate_to_chinese(self, mock_ai):
        mock_ai.return_value = """**标题** 高品质无线耳机
**描述** 卓越音质体验

ADAPTATIONS:
- 使用四字成语增强文案
- 强调正品保障

SEO_CHANGES:
- 添加中国消费者常用搜索关键词"""

        result = translate_listing(
            "**Title** Headphones", "zh-CN",
        )
        assert "标题" in result.translated
        assert len(result.adaptations) == 2

    @patch("app.translator.call_ai")
    def test_unknown_locale_fallback(self, mock_ai):
        mock_ai.return_value = "Translated content"

        result = translate_listing(
            "**Title** Test", "xx-YY",
        )
        assert result.translated == "Translated content"
        assert "Basic translation" in result.adaptations[0]

    @patch("app.translator.call_ai")
    def test_no_adaptations_in_response(self, mock_ai):
        mock_ai.return_value = "Just translated text without any sections"

        result = translate_listing("Test", "ja-JP")
        assert result.translated != ""
        # Adaptations may be empty if AI didn't include them
        assert isinstance(result.adaptations, list)


# ── Batch Translation ──────────────────────────────────────

class TestBatchTranslate:
    @patch("app.translator.call_ai")
    def test_batch_multiple_locales(self, mock_ai):
        mock_ai.return_value = "Translated content\nADAPTATIONS:\n- Change 1\nSEO_CHANGES:\n- Change 2"

        results = batch_translate(
            "**Title** Test Product",
            ["ja-JP", "de-DE", "zh-CN"],
        )
        assert len(results) == 3
        assert results[0].target_locale == "ja-JP"
        assert results[1].target_locale == "de-DE"
        assert results[2].target_locale == "zh-CN"

    @patch("app.translator.call_ai")
    def test_batch_with_platform(self, mock_ai):
        mock_ai.return_value = "Content"

        results = batch_translate(
            "Test", ["fr-FR"], platform="shopee",
        )
        assert len(results) == 1


# ── List Locales ────────────────────────────────────────────

class TestListLocales:
    def test_output_format(self):
        output = list_locales()
        assert "Available Locales" in output
        assert "en-US" in output
        assert "ja-JP" in output
        assert "$" in output
        assert "¥" in output

    def test_all_locales_listed(self):
        output = list_locales()
        for code in LOCALES:
            assert code in output
