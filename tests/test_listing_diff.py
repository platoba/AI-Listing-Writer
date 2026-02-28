"""Tests for listing_diff module."""
import pytest
from app.listing_diff import (
    parse_sections, count_words, avg_sentence_length,
    extract_keyword_set, keyword_density,
    diff_listings, diff_to_dict, diff_summary_text,
    SectionDiff, ChangeType, ImpactLevel, KeywordDelta, ReadabilityDelta,
    ListingDiffResult,
)


# ── Fixtures ─────────────────────────────────────────────────

LISTING_V1 = """**Title** Premium Wireless Bluetooth Headphones with Noise Cancellation
**Bullet Points**
- Active noise cancellation blocks outside noise
- 30 hours battery life for all-day listening
- Comfortable over-ear design with memory foam
**Description** Experience crystal-clear sound with our premium wireless headphones. Built for comfort and performance.
**Search Terms** wireless headphones, bluetooth, noise cancelling, over ear, premium audio"""

LISTING_V2 = """**Title** Premium Wireless Bluetooth Headphones - Active Noise Cancelling, 40Hr Battery, Hi-Res Audio
**Bullet Points**
- Advanced active noise cancellation with 3 modes (full, partial, transparent)
- 40 hours battery life — charges in 2 hours via USB-C
- Ultra-comfortable over-ear design with premium memory foam padding
- Hi-Res Audio certified with 40mm custom drivers
- Foldable design with premium carry case included
**Description** Experience studio-quality Hi-Res Audio with our premium wireless headphones. Features advanced 3-mode ANC, 40-hour battery, and ultra-comfortable memory foam ear cups. Built for audiophiles who demand the best.
**Search Terms** wireless headphones, bluetooth 5.3, noise cancelling, over ear, premium audio, hi-res, ANC, 40 hour battery, usb-c charging, foldable headphones
**Target Audience** Audiophiles and commuters who want premium sound quality with long battery life"""

LISTING_CN_V1 = """**标题** 无线蓝牙降噪耳机
**描述** 高品质无线耳机，适合日常使用
**标签** #无线耳机 #蓝牙 #降噪"""

LISTING_CN_V2 = """**标题** 旗舰无线蓝牙主动降噪耳机 40小时续航 Hi-Res认证
**描述** 旗舰级无线降噪耳机，搭载40mm定制驱动单元，Hi-Res认证音质。三模式ANC降噪，40小时超长续航，USB-C快充。专为发烧友打造。
**标签** #无线耳机 #蓝牙 #降噪 #HiRes #旗舰 #发烧 #长续航"""


# ── parse_sections ───────────────────────────────────────────

class TestParseSections:
    def test_parse_english_listing(self):
        sections = parse_sections(LISTING_V1)
        assert "title" in sections
        assert "bullets" in sections
        assert "description" in sections
        assert "keywords" in sections

    def test_parse_chinese_listing(self):
        sections = parse_sections(LISTING_CN_V1)
        assert "title" in sections or "body" in sections

    def test_parse_empty_text(self):
        sections = parse_sections("")
        assert "body" in sections
        assert sections["body"] == ""

    def test_parse_no_sections(self):
        sections = parse_sections("Just a plain text without any markdown sections")
        assert "body" in sections

    def test_title_extraction(self):
        sections = parse_sections(LISTING_V1)
        assert "Premium Wireless" in sections["title"]

    def test_search_terms_extraction(self):
        sections = parse_sections(LISTING_V1)
        assert "wireless headphones" in sections["keywords"]


# ── count_words ──────────────────────────────────────────────

class TestCountWords:
    def test_english_words(self):
        assert count_words("hello world") == 2

    def test_chinese_words(self):
        assert count_words("你好世界") == 4  # Each char counts as a word

    def test_mixed_words(self):
        count = count_words("hello 你好 world 世界")
        # hello, world = 2 english; 你,好,世,界 = 4 chinese = 6 total
        assert count >= 4

    def test_empty_string(self):
        assert count_words("") == 0

    def test_numbers_and_words(self):
        count = count_words("I have 3 cats and 2 dogs")
        assert count >= 5  # words + numbers


# ── avg_sentence_length ──────────────────────────────────────

class TestAvgSentenceLength:
    def test_simple_sentences(self):
        text = "I like cats. I like dogs."
        avg = avg_sentence_length(text)
        assert avg == pytest.approx(3.0, abs=0.5)

    def test_single_sentence(self):
        text = "This is a simple sentence."
        avg = avg_sentence_length(text)
        assert avg > 0

    def test_empty_text(self):
        assert avg_sentence_length("") == 0.0

    def test_chinese_sentences(self):
        text = "这是第一句话。这是第二句话。"
        avg = avg_sentence_length(text)
        assert avg > 0


# ── extract_keyword_set ──────────────────────────────────────

class TestExtractKeywordSet:
    def test_removes_stop_words(self):
        words = extract_keyword_set("the quick brown fox is a good animal")
        assert "the" not in words
        assert "is" not in words
        assert "quick" in words or "brown" in words

    def test_lowercase(self):
        words = extract_keyword_set("Hello WORLD")
        assert "hello" in words
        assert "world" in words

    def test_short_words_removed(self):
        words = extract_keyword_set("I a go to be am")
        # Single-char words removed, stop words removed; "go" and "am" are 2-char and may survive
        assert "a" not in words
        assert "I" not in words
        assert "to" not in words

    def test_chinese_keywords(self):
        words = extract_keyword_set("这是无线蓝牙降噪耳机")
        assert len(words) > 0


# ── keyword_density ──────────────────────────────────────────

class TestKeywordDensity:
    def test_basic_density(self):
        text = "wireless headphones are the best wireless headphones"
        density = keyword_density(text, ["wireless"])
        assert density > 0

    def test_zero_density(self):
        density = keyword_density("hello world", ["missing"])
        assert density == 0.0

    def test_empty_text(self):
        assert keyword_density("", ["keyword"]) == 0.0

    def test_empty_keywords(self):
        assert keyword_density("some text", []) == 0.0

    def test_multiple_keywords(self):
        text = "wireless bluetooth headphones with noise cancellation"
        density = keyword_density(text, ["wireless", "bluetooth", "headphones"])
        assert density > 0


# ── diff_listings ────────────────────────────────────────────

class TestDiffListings:
    def test_basic_diff(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        assert isinstance(result, ListingDiffResult)
        assert result.sections_changed > 0

    def test_identical_listings(self):
        result = diff_listings(LISTING_V1, LISTING_V1)
        assert result.sections_changed == 0
        assert result.improvement_score == 0

    def test_new_sections_detected(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        # V2 has "audience" section that V1 doesn't
        assert result.sections_added >= 1

    def test_improved_listing_positive_score(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        assert result.improvement_score > 0  # V2 is objectively better

    def test_degraded_listing_negative_score(self):
        # V2 → V1 is a regression
        result = diff_listings(LISTING_V2, LISTING_V1)
        assert result.improvement_score < 0 or result.sections_removed >= 1

    def test_char_deltas(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        assert result.total_char_delta > 0  # V2 is longer

    def test_word_deltas(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        assert result.total_word_delta > 0  # V2 has more content

    def test_with_target_keywords(self):
        keywords = ["wireless", "bluetooth", "hi-res", "ANC", "usb-c"]
        result = diff_listings(LISTING_V1, LISTING_V2, target_keywords=keywords)
        assert result.keyword_delta is not None
        assert len(result.keyword_delta.added_keywords) > 0

    def test_keyword_delta_coverage(self):
        keywords = ["wireless", "bluetooth", "headphones"]
        result = diff_listings(LISTING_V1, LISTING_V2, target_keywords=keywords)
        kd = result.keyword_delta
        assert kd is not None
        assert len(kd.retained_keywords) > 0  # Common keywords retained

    def test_readability_delta(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        assert result.readability_delta is not None
        assert result.readability_delta.old_avg_sentence_len >= 0
        assert result.readability_delta.new_avg_sentence_len >= 0

    def test_chinese_listing_diff(self):
        result = diff_listings(LISTING_CN_V1, LISTING_CN_V2)
        assert isinstance(result, ListingDiffResult)
        assert result.total_char_delta > 0

    def test_empty_old_listing(self):
        result = diff_listings("", LISTING_V1)
        assert result.sections_added > 0
        assert result.improvement_score > 0

    def test_empty_new_listing(self):
        result = diff_listings(LISTING_V1, "")
        # Removing all content should show sections removed or body section change
        assert result.total_char_delta < 0

    def test_both_empty(self):
        result = diff_listings("", "")
        assert result.total_char_delta == 0


# ── SectionDiff ──────────────────────────────────────────────

class TestSectionDiff:
    def test_similarity_identical(self):
        sd = SectionDiff(section="test", change_type=ChangeType.UNCHANGED,
                         old_text="hello world", new_text="hello world")
        assert sd.similarity == 1.0

    def test_similarity_different(self):
        sd = SectionDiff(section="test", change_type=ChangeType.MODIFIED,
                         old_text="hello world", new_text="goodbye universe")
        assert sd.similarity < 1.0

    def test_similarity_empty_both(self):
        sd = SectionDiff(section="test", change_type=ChangeType.UNCHANGED,
                         old_text="", new_text="")
        assert sd.similarity == 1.0

    def test_similarity_one_empty(self):
        sd = SectionDiff(section="test", change_type=ChangeType.ADDED,
                         old_text="", new_text="hello")
        assert sd.similarity == 0.0

    def test_char_delta(self):
        sd = SectionDiff(section="test", change_type=ChangeType.MODIFIED,
                         old_char_count=100, new_char_count=150)
        assert sd.char_delta == 50

    def test_word_delta(self):
        sd = SectionDiff(section="test", change_type=ChangeType.MODIFIED,
                         old_word_count=20, new_word_count=30)
        assert sd.word_delta == 10


# ── KeywordDelta ─────────────────────────────────────────────

class TestKeywordDelta:
    def test_coverage_improved(self):
        kd = KeywordDelta(
            added_keywords=["new1", "new2"],
            removed_keywords=["old1"],
        )
        assert kd.coverage_improved is True

    def test_coverage_degraded(self):
        kd = KeywordDelta(
            added_keywords=["new1"],
            removed_keywords=["old1", "old2", "old3"],
        )
        assert kd.coverage_improved is False

    def test_density_change(self):
        kd = KeywordDelta(old_density=2.0, new_density=3.5)
        assert kd.density_change == pytest.approx(1.5)


# ── ReadabilityDelta ─────────────────────────────────────────

class TestReadabilityDelta:
    def test_improved_shorter_sentences(self):
        rd = ReadabilityDelta(old_avg_sentence_len=20, new_avg_sentence_len=15)
        assert rd.readability_improved is True

    def test_degraded_longer_sentences(self):
        rd = ReadabilityDelta(old_avg_sentence_len=15, new_avg_sentence_len=20)
        assert rd.readability_improved is False

    def test_sentence_len_change(self):
        rd = ReadabilityDelta(old_avg_sentence_len=15, new_avg_sentence_len=12)
        assert rd.sentence_len_change == pytest.approx(-3.0)


# ── ListingDiffResult ────────────────────────────────────────

class TestListingDiffResult:
    def test_summary_not_empty(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        summary = result.summary()
        assert len(summary) > 50
        assert "Listing Diff Summary" in summary

    def test_total_char_delta(self):
        result = ListingDiffResult(old_total_chars=100, new_total_chars=150)
        assert result.total_char_delta == 50

    def test_total_word_delta(self):
        result = ListingDiffResult(old_total_words=20, new_total_words=35)
        assert result.total_word_delta == 15


# ── diff_to_dict ─────────────────────────────────────────────

class TestDiffToDict:
    def test_basic_dict(self):
        result = diff_listings(LISTING_V1, LISTING_V2, target_keywords=["wireless"])
        d = diff_to_dict(result)
        assert "sections_changed" in d
        assert "section_diffs" in d
        assert "keyword_delta" in d
        assert "readability" in d

    def test_dict_section_diffs(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        d = diff_to_dict(result)
        assert len(d["section_diffs"]) > 0
        first = d["section_diffs"][0]
        assert "section" in first
        assert "change_type" in first
        assert "similarity" in first

    def test_dict_without_keywords(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        d = diff_to_dict(result)
        assert d["keyword_delta"] is None

    def test_dict_values_serializable(self):
        """Ensure all values are JSON-serializable types."""
        import json
        result = diff_listings(LISTING_V1, LISTING_V2, target_keywords=["wireless"])
        d = diff_to_dict(result)
        serialized = json.dumps(d)
        assert len(serialized) > 0


# ── diff_summary_text ────────────────────────────────────────

class TestDiffSummaryText:
    def test_returns_string(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        text = diff_summary_text(result)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_contains_icons(self):
        result = diff_listings(LISTING_V1, LISTING_V2)
        text = diff_summary_text(result)
        # Should have some status icons
        assert any(icon in text for icon in ["🟢", "🟡", "⚪", "🔴", "📊"])
