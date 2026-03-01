"""Tests for readability analyzer."""
import pytest
from app.readability import (
    ReadabilityAnalyzer, ReadabilityLevel, AudienceType,
    ReadabilityReport, ReadabilityIndex, VocabularyStats, SentenceStats,
    analyze_readability,
    _count_syllables_en, _count_syllables_cn, _is_chinese,
    _tokenize_sentences, _tokenize_words, _count_complex_words,
    PLATFORM_TARGETS,
)


# ── Syllable Counting ──────────────────────────────────────

class TestSyllableCounting:
    def test_one_syllable_words(self):
        assert _count_syllables_en("cat") == 1
        assert _count_syllables_en("dog") == 1
        assert _count_syllables_en("run") == 1
        assert _count_syllables_en("the") == 1

    def test_two_syllable_words(self):
        assert _count_syllables_en("table") == 2
        assert _count_syllables_en("apple") == 2
        assert _count_syllables_en("happy") == 2
        assert _count_syllables_en("monkey") == 2

    def test_three_syllable_words(self):
        assert _count_syllables_en("beautiful") == 3
        assert _count_syllables_en("banana") == 3
        assert _count_syllables_en("umbrella") == 3

    def test_multi_syllable_words(self):
        assert _count_syllables_en("extraordinary") >= 4
        assert _count_syllables_en("communication") >= 4

    def test_silent_e(self):
        assert _count_syllables_en("make") == 1
        assert _count_syllables_en("home") == 1
        assert _count_syllables_en("time") == 1

    def test_ed_ending(self):
        assert _count_syllables_en("walked") == 1
        assert _count_syllables_en("played") == 1

    def test_empty_string(self):
        assert _count_syllables_en("") == 0

    def test_numbers(self):
        assert _count_syllables_en("123") == 0

    def test_short_words(self):
        assert _count_syllables_en("a") == 1
        assert _count_syllables_en("I") == 1
        assert _count_syllables_en("go") == 1

    def test_chinese_syllable_count(self):
        assert _count_syllables_cn("你好世界") == 4
        assert _count_syllables_cn("") == 0
        assert _count_syllables_cn("Hello 世界") == 2  # only Chinese chars


# ── Language Detection ──────────────────────────────────────

class TestLanguageDetection:
    def test_english_text(self):
        assert not _is_chinese("This is an English sentence.")

    def test_chinese_text(self):
        assert _is_chinese("这是一个中文句子。")

    def test_mixed_text_chinese_dominant(self):
        assert _is_chinese("这是中文 with some English")

    def test_mixed_text_english_dominant(self):
        assert not _is_chinese("This is English 你好")


# ── Text Tokenization ──────────────────────────────────────

class TestTokenization:
    def test_sentence_split_period(self):
        sents = _tokenize_sentences("First sentence. Second sentence. Third one.")
        assert len(sents) == 3

    def test_sentence_split_question(self):
        sents = _tokenize_sentences("What is this? It's a test! Great.")
        assert len(sents) == 3

    def test_sentence_split_chinese(self):
        sents = _tokenize_sentences("第一句话。第二句话！第三句话？")
        assert len(sents) == 3

    def test_sentence_split_newlines(self):
        sents = _tokenize_sentences("Line one\nLine two\nLine three")
        assert len(sents) == 3

    def test_sentence_split_bullets(self):
        text = "Header.\n- Point one\n- Point two\n- Point three"
        sents = _tokenize_sentences(text)
        assert len(sents) >= 3

    def test_word_tokenization_english(self):
        words = _tokenize_words("Hello world, this is a test.")
        assert "Hello" in words
        assert "world" in words
        assert len(words) >= 5

    def test_word_tokenization_chinese(self):
        words = _tokenize_words("你好世界，这是测试。")
        assert len(words) >= 6  # each character is a word

    def test_empty_text(self):
        assert _tokenize_sentences("") == []
        assert _tokenize_words("") == []


# ── Complex Words ──────────────────────────────────────────

class TestComplexWords:
    def test_simple_words_not_complex(self):
        assert _count_complex_words(["the", "cat", "sat", "on", "mat"]) == 0

    def test_complex_words_detected(self):
        words = ["extraordinary", "communication", "international", "the", "cat"]
        assert _count_complex_words(words) >= 2

    def test_ing_suffix_excluded(self):
        # "running" has 2 syllables, not complex even with -ing
        words = ["running", "playing"]
        assert _count_complex_words(words) == 0

    def test_empty_list(self):
        assert _count_complex_words([]) == 0


# ── Readability Analyzer ───────────────────────────────────

class TestReadabilityAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    @pytest.fixture
    def simple_text(self):
        return (
            "This is a great product. It works well. "
            "You will love it. Buy it now. "
            "It is easy to use. Very durable."
        )

    @pytest.fixture
    def complex_text(self):
        return (
            "The extraordinary functionality of this revolutionary product represents "
            "an unprecedented advancement in contemporary technological innovation, "
            "incorporating sophisticated algorithmic mechanisms that fundamentally "
            "transform the operational paradigm of conventional methodologies. "
            "Furthermore, the comprehensive implementation encompasses multifaceted "
            "capabilities that substantially enhance performance characteristics "
            "through the strategic utilization of advanced computational frameworks."
        )

    @pytest.fixture
    def chinese_text(self):
        return (
            "这款产品非常好用。采用优质材料制造。"
            "适合所有年龄段的用户使用。"
            "耐用性强，质量保证。立即购买。"
        )

    def test_analyze_simple_english(self, analyzer, simple_text):
        report = analyzer.analyze(simple_text, platform="amazon")
        assert report.language == "en"
        assert report.text_length > 0
        assert report.overall_grade > 0
        assert report.overall_level in ReadabilityLevel
        assert len(report.indices) >= 4

    def test_analyze_complex_english(self, analyzer, complex_text):
        report = analyzer.analyze(complex_text, platform="amazon")
        assert report.overall_grade > 10  # Should be difficult

    def test_simple_easier_than_complex(self, analyzer, simple_text, complex_text):
        simple = analyzer.analyze(simple_text)
        complex_r = analyzer.analyze(complex_text)
        assert simple.overall_grade < complex_r.overall_grade

    def test_analyze_chinese(self, analyzer, chinese_text):
        report = analyzer.analyze(chinese_text, platform="shopee")
        assert report.language == "zh"
        assert "Chinese Readability" in report.indices or "Sentence Complexity" in report.indices

    def test_analyze_empty_text(self, analyzer):
        report = analyzer.analyze("")
        assert report.text_length == 0
        assert len(report.recommendations) > 0

    def test_analyze_whitespace_only(self, analyzer):
        report = analyzer.analyze("   \n  \t  ")
        assert report.text_length == 0
        assert any("no text" in r.lower() for r in report.recommendations)

    def test_flesch_reading_ease(self, analyzer, simple_text):
        report = analyzer.analyze(simple_text)
        fre = report.indices.get("Flesch Reading Ease")
        assert fre is not None
        assert 0 <= fre.score <= 100

    def test_flesch_kincaid_grade(self, analyzer, simple_text):
        report = analyzer.analyze(simple_text)
        fkgl = report.indices.get("Flesch-Kincaid Grade")
        assert fkgl is not None
        assert fkgl.grade_level >= 0

    def test_gunning_fog(self, analyzer, simple_text):
        report = analyzer.analyze(simple_text)
        fog = report.indices.get("Gunning Fog")
        assert fog is not None
        assert fog.score >= 0

    def test_coleman_liau(self, analyzer, simple_text):
        report = analyzer.analyze(simple_text)
        cli = report.indices.get("Coleman-Liau")
        assert cli is not None

    def test_smog(self, analyzer, complex_text):
        report = analyzer.analyze(complex_text)
        smog = report.indices.get("SMOG")
        assert smog is not None

    def test_ari(self, analyzer, simple_text):
        report = analyzer.analyze(simple_text)
        ari = report.indices.get("ARI")
        assert ari is not None


# ── Vocabulary Stats ────────────────────────────────────────

class TestVocabularyStats:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_vocabulary_stats_present(self, analyzer):
        report = analyzer.analyze("This is a simple product. It works well and is very durable.")
        assert report.vocabulary is not None
        assert report.vocabulary.total_words > 0
        assert report.vocabulary.unique_words > 0

    def test_lexical_diversity(self, analyzer):
        # Text with repeated words should have lower diversity
        repetitive = "good good good good product product product product"
        diverse = "excellent remarkable stunning wonderful magnificent"
        rep_report = analyzer.analyze(repetitive)
        div_report = analyzer.analyze(diverse)
        assert rep_report.vocabulary.lexical_diversity < div_report.vocabulary.lexical_diversity

    def test_complex_word_count(self, analyzer):
        report = analyzer.analyze(
            "The extraordinary functionality of this revolutionary product "
            "represents an unprecedented advancement in technology."
        )
        assert report.vocabulary.complex_words > 0
        assert report.vocabulary.complex_word_pct > 0

    def test_avg_word_length(self, analyzer):
        short = "It is a good bag."
        long = "Extraordinarily sophisticated revolutionary technological advancement."
        short_r = analyzer.analyze(short)
        long_r = analyzer.analyze(long)
        assert short_r.vocabulary.avg_word_length < long_r.vocabulary.avg_word_length

    def test_most_used_words(self, analyzer):
        report = analyzer.analyze(
            "This premium quality product features premium materials. "
            "Premium craftsmanship ensures quality results. Premium design."
        )
        assert report.vocabulary.most_used is not None
        # "premium" should be in most used
        found = any("premium" in w[0] for w in report.vocabulary.most_used)
        assert found


# ── Sentence Stats ──────────────────────────────────────────

class TestSentenceStats:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_sentence_count(self, analyzer):
        report = analyzer.analyze("First sentence. Second sentence. Third sentence.")
        assert report.sentences.total_sentences == 3

    def test_avg_sentence_length(self, analyzer):
        report = analyzer.analyze("This is short. This is also quite short.")
        assert report.sentences.avg_words_per_sentence > 0

    def test_long_sentences_detected(self, analyzer):
        long_sent = " ".join(["word"] * 30)
        report = analyzer.analyze(f"{long_sent}. Short.")
        assert report.sentences.very_long_sentences >= 1

    def test_short_sentences_detected(self, analyzer):
        report = analyzer.analyze("Yes. No. OK. Good. Sure. This is a normal sentence with several words.")
        assert report.sentences.very_short_sentences >= 3

    def test_min_max_sentence_length(self, analyzer):
        report = analyzer.analyze(
            "Short. This is a somewhat longer sentence with more words in it."
        )
        assert report.sentences.min_sentence_length < report.sentences.max_sentence_length


# ── Reading Time ────────────────────────────────────────────

class TestReadingTime:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_reading_time_positive(self, analyzer):
        report = analyzer.analyze("A decent product with good features. Worth buying.")
        assert report.reading_time_seconds > 0

    def test_longer_text_more_time(self, analyzer):
        short = "Short text."
        long = " ".join(["This is a word."] * 50)
        short_r = analyzer.analyze(short)
        long_r = analyzer.analyze(long)
        assert long_r.reading_time_seconds > short_r.reading_time_seconds

    def test_chinese_reading_time(self, analyzer):
        report = analyzer.analyze("这是一段中文文本。用来测试阅读时间。")
        assert report.reading_time_seconds > 0


# ── Platform Fit ────────────────────────────────────────────

class TestPlatformFit:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_platform_fit_scores(self, analyzer):
        report = analyzer.analyze("This is a simple, easy to read product listing.")
        assert len(report.platform_fit) > 0
        for score in report.platform_fit.values():
            assert 0 <= score <= 100

    def test_all_platforms_scored(self, analyzer):
        report = analyzer.analyze("A standard product description with several sentences. It works well.")
        for platform in PLATFORM_TARGETS:
            assert platform in report.platform_fit

    def test_simple_text_fits_casual_platforms(self, analyzer):
        simple = "Good product. Works great. Easy to use. Buy now."
        report = analyzer.analyze(simple)
        # Simple text should fit Shopee/Temu better than complex
        assert report.platform_fit.get("shopee", 0) >= 50

    def test_complex_text_penalized(self, analyzer):
        complex_text = (
            "The extraordinary multifunctionality of this sophisticated "
            "apparatus encompasses comprehensive capabilities that fundamentally "
            "revolutionize contemporary operational methodologies through strategic "
            "implementation of advanced technological frameworks."
        )
        report = analyzer.analyze(complex_text)
        assert report.platform_fit.get("temu", 0) < 80


# ── Recommendations ─────────────────────────────────────────

class TestRecommendations:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_recommendations_generated(self, analyzer):
        report = analyzer.analyze("A simple product.")
        assert len(report.recommendations) > 0

    def test_complex_text_gets_simplification_recs(self, analyzer):
        complex_text = (
            "The extraordinarily sophisticated multifunctional apparatus represents "
            "an unprecedented revolutionary advancement in contemporary technological "
            "innovation that substantially transforms conventional methodologies."
        )
        report = analyzer.analyze(complex_text, platform="shopee")
        # Should recommend simplification
        recs_text = " ".join(report.recommendations).lower()
        assert "complex" in recs_text or "simpl" in recs_text or "grade" in recs_text or "shorten" in recs_text

    def test_audience_specific_recs(self, analyzer):
        report = analyzer.analyze(
            "Advanced technical specifications for the professional market.",
            audience=AudienceType.YOUTH,
        )
        recs_text = " ".join(report.recommendations).lower()
        assert len(report.recommendations) > 0


# ── Readability Level ───────────────────────────────────────

class TestReadabilityLevel:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_level_is_valid_enum(self, analyzer):
        report = analyzer.analyze("A test sentence. Another one.")
        assert isinstance(report.overall_level, ReadabilityLevel)

    def test_grade_to_level_mapping(self, analyzer):
        # Very easy
        assert analyzer._grade_to_level(3) == ReadabilityLevel.VERY_EASY
        # Easy
        assert analyzer._grade_to_level(6) == ReadabilityLevel.EASY
        # Standard
        assert analyzer._grade_to_level(10) == ReadabilityLevel.STANDARD
        # Difficult
        assert analyzer._grade_to_level(12) == ReadabilityLevel.DIFFICULT
        # Very difficult
        assert analyzer._grade_to_level(15) == ReadabilityLevel.VERY_DIFFICULT


# ── Report Formatting ───────────────────────────────────────

class TestReportFormatting:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_summary_contains_key_info(self, analyzer):
        report = analyzer.analyze("This is a good product. Works very well.")
        summary = report.summary()
        assert "Readability Report" in summary
        assert "Grade" in summary or "Level" in summary
        assert "Reading Time" in summary

    def test_summary_includes_indices(self, analyzer):
        report = analyzer.analyze("A decent test product with several words in the description.")
        summary = report.summary()
        assert "Readability Indices" in summary

    def test_summary_includes_vocabulary(self, analyzer):
        report = analyzer.analyze("A good product with nice features. Well made and durable.")
        summary = report.summary()
        assert "Vocabulary" in summary

    def test_summary_includes_platform_fit(self, analyzer):
        report = analyzer.analyze("Simple text for analysis.")
        summary = report.summary()
        assert "Platform Fit" in summary


# ── Text Comparison ─────────────────────────────────────────

class TestTextComparison:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_compare_two_texts(self, analyzer):
        texts = {
            "Simple": "Good product. Works well. Buy it.",
            "Complex": "The extraordinary multifunctional apparatus represents an unprecedented advancement.",
        }
        result = analyzer.compare_texts(texts, platform="amazon")
        assert "Simple" in result
        assert "Complex" in result
        assert "Readability Comparison" in result

    def test_compare_empty_dict(self, analyzer):
        result = analyzer.compare_texts({})
        assert "No texts" in result

    def test_compare_includes_winner(self, analyzer):
        texts = {
            "A": "Simple easy product.",
            "B": "Extraordinarily sophisticated revolutionary mechanism.",
        }
        result = analyzer.compare_texts(texts, platform="amazon")
        assert "Best fit" in result


# ── Convenience Function ────────────────────────────────────

class TestConvenienceFunction:
    def test_analyze_readability_works(self):
        report = analyze_readability("This is a test product listing.")
        assert isinstance(report, ReadabilityReport)
        assert report.text_length > 0
        assert report.language == "en"

    def test_analyze_readability_with_platform(self):
        report = analyze_readability("简单的产品描述。", platform="shopee")
        assert report.language == "zh"

    def test_analyze_readability_with_audience(self):
        report = analyze_readability(
            "Professional grade equipment.",
            audience=AudienceType.PROFESSIONAL,
        )
        assert isinstance(report, ReadabilityReport)


# ── Edge Cases ──────────────────────────────────────────────

class TestEdgeCases:
    @pytest.fixture
    def analyzer(self):
        return ReadabilityAnalyzer()

    def test_single_word(self, analyzer):
        report = analyzer.analyze("Product")
        assert report.text_length > 0

    def test_very_long_text(self, analyzer):
        text = "This is a sentence. " * 500
        report = analyzer.analyze(text)
        assert report.reading_time_seconds > 100

    def test_special_characters(self, analyzer):
        report = analyzer.analyze("★★★★★ Best product! 🎉 50% off! $29.99 → $14.99")
        assert report.text_length > 0

    def test_mixed_language(self, analyzer):
        report = analyzer.analyze("This product 非常好 and works perfectly 完美运行")
        assert report.text_length > 0

    def test_html_in_text(self, analyzer):
        report = analyzer.analyze("<b>Bold product</b>. <p>A paragraph.</p>")
        assert report.text_length > 0

    def test_numbered_list(self, analyzer):
        text = "Features:\n1. Durable material\n2. Easy to clean\n3. Lightweight design"
        report = analyzer.analyze(text)
        assert report.text_length > 0

    def test_bullet_list(self, analyzer):
        text = "Features:\n- Durable\n- Easy to clean\n- Lightweight"
        report = analyzer.analyze(text)
        assert report.sentences is not None

    def test_all_caps_text(self, analyzer):
        report = analyzer.analyze("THIS IS ALL CAPS TEXT FOR A PRODUCT LISTING")
        assert report.text_length > 0

    def test_unicode_text(self, analyzer):
        report = analyzer.analyze("Résumé café naïve piñata über straße")
        assert report.text_length > 0
