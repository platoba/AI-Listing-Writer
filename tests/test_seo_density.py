"""Tests for SEO Density Analyzer."""
import pytest
from app.seo_density import (
    analyze_density,
    format_density_report,
    KeywordDensity, NGramResult, DensityReport,
    _tokenize, _extract_ngrams, _extract_sections,
    _compute_tf_idf, _suggest_lsi_keywords,
    PLATFORM_DENSITY, LSI_CLUSTERS,
)


class TestTokenization:
    def test_tokenize_english(self):
        tokens = _tokenize("Hello world, this is a test", remove_stops=False)
        assert "hello" in tokens
        assert "world" in tokens

    def test_tokenize_remove_stops(self):
        tokens = _tokenize("the cat and the dog", remove_stops=True)
        assert "cat" in tokens
        assert "dog" in tokens
        assert "the" not in tokens
        assert "and" not in tokens

    def test_tokenize_chinese(self):
        tokens = _tokenize("这是中文测试", remove_stops=False)
        assert len(tokens) > 0

    def test_tokenize_empty(self):
        tokens = _tokenize("", remove_stops=True)
        assert tokens == []


class TestNGramExtraction:
    def test_extract_unigrams(self):
        tokens = ["hello", "world", "hello"]
        ngrams = _extract_ngrams(tokens, 1)
        assert ngrams["hello"] == 2
        assert ngrams["world"] == 1

    def test_extract_bigrams(self):
        tokens = ["hello", "world", "hello", "world"]
        bigrams = _extract_ngrams(tokens, 2)
        assert bigrams["hello world"] == 2

    def test_extract_trigrams(self):
        tokens = ["this", "is", "a", "test"]
        trigrams = _extract_ngrams(tokens, 3)
        assert trigrams["this is a"] == 1

    def test_ngrams_insufficient_tokens(self):
        tokens = ["one"]
        bigrams = _extract_ngrams(tokens, 2)
        assert len(bigrams) == 0


class TestSectionExtraction:
    def test_extract_markdown_sections(self):
        text = "**Features**:\nGreat features\n**Specs**:\nAmazing specs"
        sections = _extract_sections(text)
        assert "Features" in sections
        assert "Specs" in sections

    def test_extract_no_sections(self):
        text = "Just plain text without sections"
        sections = _extract_sections(text)
        assert len(sections) > 0  # Should fall back to "Full Text"

    def test_extract_chinese_sections(self):
        text = "**产品特点**：很棒\n**规格**：优秀"
        sections = _extract_sections(text)
        assert "产品特点" in sections or len(sections) > 0


class TestTFIDF:
    def test_compute_tf_idf(self):
        score = _compute_tf_idf(term_freq=5, total_terms=100, doc_freq=2, total_docs=10)
        assert score > 0

    def test_high_frequency_term(self):
        common = _compute_tf_idf(10, 100, 8, 10)  # Common term
        rare = _compute_tf_idf(10, 100, 1, 10)    # Rare term
        # Rare terms should have higher TF-IDF
        assert rare > common

    def test_zero_frequency(self):
        score = _compute_tf_idf(0, 100, 1, 10)
        assert score >= 0


class TestBasicDensityAnalysis:
    def test_analyze_simple_text(self):
        text = "Wireless headphones bluetooth wireless audio headphones"
        report = analyze_density(
            text,
            target_keywords=["wireless", "bluetooth", "headphones"],
            platform="amazon",
            top_n=10
        )
        assert isinstance(report, DensityReport)
        assert report.total_words > 0
        assert len(report.target_keyword_analysis) == 3

    def test_keyword_density_calculation(self):
        text = "Wireless headphones. " * 10 + "bluetooth " * 5
        report = analyze_density(text, target_keywords=["wireless", "bluetooth"])
        wireless_kw = next(k for k in report.target_keyword_analysis if k.keyword == "wireless")
        bluetooth_kw = next(k for k in report.target_keyword_analysis if k.keyword == "bluetooth")
        # Wireless appears more often
        assert wireless_kw.count > bluetooth_kw.count

    def test_no_target_keywords(self):
        text = "Just some random text without specific keywords"
        report = analyze_density(text, target_keywords=None)
        assert report.total_words > 0
        assert len(report.target_keyword_analysis) == 0


class TestKeywordStatus:
    def test_optimal_density(self):
        # 2% density is optimal for most platforms
        text = "keyword " * 2 + "other words " * 98
        report = analyze_density(text, target_keywords=["keyword"])
        kw = report.target_keyword_analysis[0]
        assert kw.status in ["optimal", "low"]  # Depends on exact calculation

    def test_stuffing_detection(self):
        text = "keyword " * 50  # 50% density = stuffing
        report = analyze_density(text, target_keywords=["keyword"])
        kw = report.target_keyword_analysis[0]
        assert kw.status == "stuffing"

    def test_low_density(self):
        text = "keyword " + "other " * 200
        report = analyze_density(text, target_keywords=["keyword"])
        kw = report.target_keyword_analysis[0]
        assert kw.status == "low"

    def test_high_density(self):
        text = "keyword " * 10 + "other " * 40
        report = analyze_density(text, target_keywords=["keyword"])
        kw = report.target_keyword_analysis[0]
        assert kw.status in ["high", "optimal"]


class TestNGramAnalysis:
    def test_unigrams_populated(self):
        text = "wireless bluetooth headphones premium wireless bluetooth"
        report = analyze_density(text)
        assert len(report.top_ngrams.unigrams) > 0

    def test_bigrams_populated(self):
        text = "wireless headphones bluetooth headphones wireless headphones"
        report = analyze_density(text)
        assert len(report.top_ngrams.bigrams) > 0

    def test_trigrams_populated(self):
        text = "premium wireless bluetooth headphones premium wireless bluetooth headphones"
        report = analyze_density(text)
        assert len(report.top_ngrams.trigrams) > 0

    def test_top_n_limit(self):
        text = " ".join([f"word{i}" for i in range(50)])
        report = analyze_density(text, top_n=5)
        assert len(report.top_ngrams.unigrams) <= 5


class TestStuffingAlerts:
    def test_stuffing_alert_triggered(self):
        text = "keyword " * 100
        report = analyze_density(text, target_keywords=["keyword"])
        assert len(report.stuffing_alerts) > 0

    def test_no_stuffing_alerts(self):
        text = "keyword " * 2 + "other words " * 100
        report = analyze_density(text, target_keywords=["keyword"])
        assert len(report.stuffing_alerts) == 0

    def test_multiple_keywords_stuffing(self):
        text = "keyword1 " * 50 + "keyword2 " * 50
        report = analyze_density(text, target_keywords=["keyword1", "keyword2"])
        # Both should trigger alerts
        assert len(report.stuffing_alerts) >= 2


class TestLSISuggestions:
    def test_lsi_suggestions_generated(self):
        text = "wireless earbuds for music"
        suggestions = _suggest_lsi_keywords(text, ["wireless earbuds"])
        assert len(suggestions) > 0
        # Should suggest related terms like "bluetooth", "noise cancelling"
        assert any(s in suggestions for s in ["bluetooth", "noise cancelling", "battery"])

    def test_no_lsi_for_unknown_keywords(self):
        text = "random product description"
        suggestions = _suggest_lsi_keywords(text, ["randomkeyword"])
        # May or may not have suggestions
        assert isinstance(suggestions, list)

    def test_lsi_excludes_existing_terms(self):
        text = "wireless earbuds with bluetooth"
        suggestions = _suggest_lsi_keywords(text, ["wireless earbuds"])
        # "bluetooth" already in text, shouldn't be suggested
        assert "bluetooth" not in suggestions


class TestSectionBreakdown:
    def test_section_breakdown_populated(self):
        text = "**Features**: wireless bluetooth\n**Specs**: premium quality"
        report = analyze_density(text)
        assert len(report.section_breakdown) > 0

    def test_section_word_counts(self):
        text = "**Section1**: one two three\n**Section2**: four five"
        report = analyze_density(text)
        if len(report.section_breakdown) > 1:
            for section_name, data in report.section_breakdown.items():
                assert data["word_count"] > 0
                assert "unique_words" in data


class TestOverallHealth:
    def test_healthy_listing(self):
        text = "Premium wireless bluetooth headphones with noise cancelling. " * 20
        report = analyze_density(
            text,
            target_keywords=["wireless", "bluetooth", "headphones"],
            platform="amazon"
        )
        assert report.overall_health in ["healthy", "warning"]

    def test_critical_listing(self):
        text = "keyword " * 100  # Massive stuffing
        report = analyze_density(text, target_keywords=["keyword"])
        assert report.overall_health == "critical"

    def test_warning_listing(self):
        text = "keyword " * 10 + "other " * 50
        report = analyze_density(text, target_keywords=["keyword"])
        # High but not critical
        assert report.overall_health in ["warning", "healthy"]


class TestRecommendations:
    def test_recommendations_for_stuffing(self):
        text = "keyword " * 100
        report = analyze_density(text, target_keywords=["keyword"])
        assert any("stuffing" in r.lower() or "repetition" in r.lower() for r in report.recommendations)

    def test_recommendations_for_low_density(self):
        text = "keyword " + "other " * 200
        report = analyze_density(text, target_keywords=["keyword"])
        assert any("increase" in r.lower() for r in report.recommendations)

    def test_recommendations_for_short_content(self):
        text = "short content here"
        report = analyze_density(text)
        assert any("add more" in r.lower() or "expand" in r.lower() for r in report.recommendations)

    def test_recommendations_for_lsi(self):
        text = "wireless earbuds for music listening"
        report = analyze_density(text, target_keywords=["wireless earbuds"])
        # Should suggest related terms
        assert any("related terms" in r.lower() or "add" in r.lower() for r in report.recommendations)


class TestPlatformDensityThresholds:
    def test_amazon_thresholds(self):
        thresholds = PLATFORM_DENSITY["amazon"]
        assert "min" in thresholds
        assert "max" in thresholds
        assert "ideal" in thresholds

    def test_different_platforms(self):
        amazon = PLATFORM_DENSITY["amazon"]
        ebay = PLATFORM_DENSITY["ebay"]
        assert amazon["ideal"] != ebay["ideal"] or amazon["max"] != ebay["max"]

    def test_unknown_platform_fallback(self):
        text = "keyword " * 5 + "other " * 95
        report = analyze_density(text, target_keywords=["keyword"], platform="unknown_platform")
        # Should use default and still work
        assert report.platform == "unknown_platform"


class TestVocabularyRichness:
    def test_high_vocabulary_richness(self):
        text = " ".join([f"word{i}" for i in range(100)])
        report = analyze_density(text)
        # All unique words
        assert report.vocabulary_richness > 0.9

    def test_low_vocabulary_richness(self):
        text = "same word " * 100
        report = analyze_density(text)
        # Very repetitive
        assert report.vocabulary_richness < 0.2

    def test_richness_recommendation(self):
        text = "same " * 100
        report = analyze_density(text)
        # Should recommend more varied vocabulary
        assert any("vocabulary" in r.lower() or "varied" in r.lower() for r in report.recommendations)


class TestReportFormatting:
    def test_format_density_report(self):
        text = "wireless bluetooth headphones premium quality"
        report = analyze_density(text, target_keywords=["wireless", "bluetooth"])
        formatted = format_density_report(report)
        assert "SEO Keyword Density Report" in formatted
        assert "Target Keywords:" in formatted
        assert str(report.total_words) in formatted

    def test_report_includes_health(self):
        text = "sample text here"
        report = analyze_density(text)
        formatted = format_density_report(report)
        assert "Health:" in formatted
        assert report.overall_health.upper() in formatted

    def test_report_includes_ngrams(self):
        text = "wireless bluetooth headphones"
        report = analyze_density(text)
        formatted = format_density_report(report)
        assert "Unigrams:" in formatted
        assert "Bigrams:" in formatted


class TestPhraseKeywords:
    def test_multi_word_keyword(self):
        text = "wireless earbuds bluetooth earbuds wireless earbuds"
        report = analyze_density(text, target_keywords=["wireless earbuds"])
        kw = report.target_keyword_analysis[0]
        assert kw.count > 0
        assert kw.keyword == "wireless earbuds"

    def test_phrase_density_calculation(self):
        text = "wireless earbuds " * 5 + "other words " * 95
        report = analyze_density(text, target_keywords=["wireless earbuds"])
        kw = report.target_keyword_analysis[0]
        # Phrase appears 5 times, 2 words each = 10 words out of ~105
        assert kw.density > 0


class TestEdgeCases:
    def test_empty_text(self):
        report = analyze_density("", target_keywords=["keyword"])
        assert report.total_words == 0
        assert report.unique_words == 0

    def test_very_long_text(self):
        text = "word " * 10000
        report = analyze_density(text, target_keywords=["word"])
        assert report.total_words > 9000

    def test_special_characters(self):
        text = "Product™ with Special® Characters & Symbols™"
        report = analyze_density(text, target_keywords=["product", "special"])
        assert report.total_words > 0

    def test_mixed_language(self):
        text = "English text 中文文本 mixed content"
        report = analyze_density(text)
        assert report.total_words > 0

    def test_numbers_in_text(self):
        text = "Product 2024 with 5 features and 10 benefits"
        report = analyze_density(text, target_keywords=["product", "features"])
        assert report.total_words > 0

    def test_case_insensitivity(self):
        text = "Wireless WIRELESS wireless"
        report = analyze_density(text, target_keywords=["wireless"])
        kw = report.target_keyword_analysis[0]
        assert kw.count == 3  # Should count all case variations
