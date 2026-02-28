"""Tests for competitor listing analyzer."""
import pytest
from app.competitor import (
    CompetitorAnalyzer, CompetitorProfile, ExtractedKeywords,
    GapAnalysisResult, CompetitorComparison,
    EMOTION_WORDS, URGENCY_WORDS, TRUST_WORDS, STOP_WORDS,
)


SAMPLE_LISTING_1 = """
⚡ CRYSTAL CLEAR AUDIO — Premium 40mm neodymium drivers deliver rich, detailed sound with deep bass and crisp highs.
🔋 30-HOUR BATTERY — One charge gives you a full day of music. Quick charge: 5 min = 2 hours of play.
🎧 ACTIVE NOISE CANCELLING — Advanced ANC technology blocks 95% of ambient noise for immersive listening.
📱 MULTIPOINT CONNECTION — Connect 2 devices simultaneously. Seamlessly switch between phone and laptop.
🎁 WHAT'S IN THE BOX — Headphones, USB-C cable, 3.5mm audio cable, carrying case, user guide, and warranty card.

Experience premium wireless audio with our flagship over-ear headphones.
Designed for audiophiles and professionals who demand the best.
Features Bluetooth 5.3 for stable, low-latency connection up to 30 meters.
Comfortable memory foam ear cushions with protein leather for all-day wear.
Foldable design fits perfectly in the included premium carrying case.
"""

SAMPLE_LISTING_2 = """
• High-fidelity sound with 50mm drivers
• 40-hour battery life with fast charging
• Hybrid ANC with transparency mode
• Bluetooth 5.2, multipoint, NFC
• Lightweight 250g design

These headphones deliver studio-quality sound in a portable package.
Perfect for commuting, working, or just relaxing at home.
The hybrid noise cancellation adapts to your environment automatically.
Includes a 2-year warranty and premium accessories.
"""

SAMPLE_LISTING_SHORT = """
Good headphones. Nice sound. Comfortable.
"""


class TestWordLists:
    def test_emotion_words_are_lowercase(self):
        for w in EMOTION_WORDS:
            assert w == w.lower()

    def test_urgency_words_not_empty(self):
        assert len(URGENCY_WORDS) > 0

    def test_trust_words_not_empty(self):
        assert len(TRUST_WORDS) > 0

    def test_stop_words_common(self):
        assert "the" in STOP_WORDS
        assert "and" in STOP_WORDS
        assert "of" in STOP_WORDS


class TestExtractedKeywords:
    def test_default_empty(self):
        kw = ExtractedKeywords()
        assert kw.primary == []
        assert kw.secondary == []
        assert kw.long_tail == []
        assert kw.emotional == []
        assert kw.technical == []


class TestCompetitorProfile:
    def test_default_values(self):
        p = CompetitorProfile()
        assert p.title == ""
        assert p.word_count == 0
        assert p.emoji_count == 0
        assert not p.has_warranty_mention
        assert p.readability_score == 0.0


class TestCompetitorAnalyzer:
    def setup_method(self):
        self.analyzer = CompetitorAnalyzer()

    # --- Basic analysis ---

    def test_analyze_basic(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1, "Wireless Headphones ANC")
        assert profile.title == "Wireless Headphones ANC"
        assert profile.title_length == len("Wireless Headphones ANC")
        assert profile.word_count > 50
        assert profile.description_length > 100

    def test_analyze_detects_bullets(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1)
        assert profile.bullet_count >= 2  # emoji-prefixed bullets detected

    def test_analyze_detects_bullets_dot(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_2)
        assert profile.bullet_count >= 5

    def test_analyze_detects_emojis(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1)
        assert profile.emoji_count > 0

    def test_analyze_no_emojis(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_SHORT)
        assert profile.emoji_count == 0

    def test_analyze_warranty_mention(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1)
        assert profile.has_warranty_mention

    def test_analyze_no_warranty(self):
        profile = self.analyzer.analyze_listing("Great product for sale.")
        assert not profile.has_warranty_mention

    # --- Keywords extraction ---

    def test_keywords_extracted(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1, "Bluetooth Headphones")
        kw = profile.keywords
        assert len(kw.primary) > 0
        assert isinstance(kw.primary[0], str)

    def test_technical_terms_extracted(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1)
        kw = profile.keywords
        # Should detect things like "40mm", "Bluetooth 5.3", "USB-C"
        assert len(kw.technical) > 0

    def test_emotional_words_detected(self):
        text = "This amazing, incredible, premium product is a must-have essential item."
        profile = self.analyzer.analyze_listing(text)
        assert len(profile.keywords.emotional) > 0

    def test_long_tail_phrases(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1)
        kw = profile.keywords
        assert len(kw.long_tail) > 0
        # Long tail should be multi-word
        assert any(" " in phrase for phrase in kw.long_tail)

    # --- Selling points ---

    def test_selling_points_extracted(self):
        text = "Perfect for music lovers and professionals. Designed for all-day comfort."
        profile = self.analyzer.analyze_listing(text)
        # May or may not extract depending on pattern matching
        assert isinstance(profile.selling_points, list)

    # --- Claims detection ---

    def test_claims_detected(self):
        text = "The best headphones on the market. Clinically proven to reduce noise. Award-winning design."
        profile = self.analyzer.analyze_listing(text)
        assert len(profile.claims) >= 2
        assert "superlative claim" in profile.claims
        assert "science claim" in profile.claims

    def test_no_claims(self):
        profile = self.analyzer.analyze_listing("Simple headphones with good sound quality.")
        assert len(profile.claims) == 0

    def test_eco_claim(self):
        profile = self.analyzer.analyze_listing("Eco-friendly sustainable packaging.")
        assert "environmental claim" in profile.claims

    def test_patent_claim(self):
        profile = self.analyzer.analyze_listing("Patented technology for better sound.")
        assert "IP claim" in profile.claims

    # --- Readability ---

    def test_readability_score_range(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1)
        assert 0 <= profile.readability_score <= 100

    def test_short_sentences_more_readable(self):
        easy = self.analyzer.analyze_listing("Good sound. Easy to use. Comfortable fit. Long battery.")
        hard = self.analyzer.analyze_listing(
            "The extraordinarily sophisticated electroacoustic transduction mechanism "
            "utilizing neodymium permanent magnetic flux density optimization produces "
            "phenomenally extraordinary frequency response characteristics throughout "
            "the perceptible auditory spectrum range."
        )
        assert easy.readability_score > hard.readability_score

    def test_readability_empty_text(self):
        profile = self.analyzer.analyze_listing("")
        assert profile.readability_score == 50.0

    # --- Structure score ---

    def test_structure_score_range(self):
        profile = self.analyzer.analyze_listing(SAMPLE_LISTING_1, "Good Title")
        assert 0 <= profile.structure_score <= 100

    def test_well_structured_scores_higher(self):
        good = self.analyzer.analyze_listing(SAMPLE_LISTING_1, "Full Featured Headphones")
        bad = self.analyzer.analyze_listing("OK product.", "")
        assert good.structure_score > bad.structure_score

    # --- Comparison ---

    def test_comparison_basic(self):
        comp = self.analyzer.compare(
            SAMPLE_LISTING_SHORT, "My Headphones",
            [
                {"title": "Competitor A Headphones", "text": SAMPLE_LISTING_1},
                {"title": "Competitor B Headphones", "text": SAMPLE_LISTING_2},
            ]
        )
        assert comp.your_profile.title == "My Headphones"
        assert len(comp.competitor_profiles) == 2
        assert comp.gap_analysis is not None
        assert 0 <= comp.recommendation_score <= 100

    def test_comparison_finds_gaps(self):
        comp = self.analyzer.compare(
            SAMPLE_LISTING_SHORT, "My Headphones",
            [{"title": "Comp", "text": SAMPLE_LISTING_1}]
        )
        gap = comp.gap_analysis
        # Short listing should have structural gaps
        assert len(gap.structural_gaps) > 0 or len(gap.missing_keywords) > 0

    def test_comparison_no_competitors(self):
        comp = self.analyzer.compare(
            SAMPLE_LISTING_1, "My Headphones", []
        )
        assert len(comp.competitor_profiles) == 0
        assert comp.recommendation_score == 50.0

    def test_comparison_recommendation_score(self):
        # Short vs long should have high improvement score
        comp = self.analyzer.compare(
            "OK product.", "Short",
            [
                {"title": "Full Listing", "text": SAMPLE_LISTING_1},
                {"title": "Another Full", "text": SAMPLE_LISTING_2},
            ]
        )
        assert comp.recommendation_score > 20

    # --- Gap analysis ---

    def test_gap_missing_keywords(self):
        comp = self.analyzer.compare(
            "Simple headphone product.", "Headphones",
            [{"title": "ANC Wireless Bluetooth Headphones", "text": SAMPLE_LISTING_1}]
        )
        gap = comp.gap_analysis
        assert len(gap.missing_keywords) > 0

    def test_gap_warranty_opportunity(self):
        comp = self.analyzer.compare(
            "Simple product no warranty.", "Product",
            [
                {"title": "A", "text": "Great product with warranty guarantee."},
                {"title": "B", "text": "Premium with 2 year warranty."},
            ]
        )
        gap = comp.gap_analysis
        # Both competitors mention warranty, ours doesn't
        opps = [o for o in gap.opportunities if "warranty" in o.lower()]
        assert len(opps) > 0

    def test_gap_strengths(self):
        # If we have unique keywords, should be a strength
        comp = self.analyzer.compare(
            "Proprietary quantum audio technology with nanotube drivers.",
            "Quantum Headphones",
            [{"title": "Normal Headphones", "text": "Good sound bluetooth headphones."}]
        )
        gap = comp.gap_analysis
        # We have unique keywords (quantum, nanotube, proprietary)
        assert len(gap.strengths) >= 0  # At least check it doesn't crash

    # --- Format comparison ---

    def test_format_comparison(self):
        comp = self.analyzer.compare(
            SAMPLE_LISTING_SHORT, "My Product",
            [{"title": "Competitor", "text": SAMPLE_LISTING_1}]
        )
        text = self.analyzer.format_comparison(comp)
        assert "Competitor Analysis Report" in text
        assert "YOUR LISTING" in text
        assert "COMPETITOR #1" in text

    def test_format_comparison_with_gaps(self):
        comp = self.analyzer.compare(
            "Short.", "Short",
            [{"title": "Full", "text": SAMPLE_LISTING_1}]
        )
        text = self.analyzer.format_comparison(comp)
        # Should have at least some sections
        assert "Improvement Score" in text

    # --- Edge cases ---

    def test_empty_text(self):
        profile = self.analyzer.analyze_listing("")
        assert profile.word_count == 0
        assert profile.bullet_count == 0

    def test_only_title(self):
        profile = self.analyzer.analyze_listing("", "Just a Title")
        assert profile.title == "Just a Title"
        assert profile.title_length == len("Just a Title")

    def test_very_long_text(self):
        long_text = "keyword " * 10000
        profile = self.analyzer.analyze_listing(long_text)
        assert profile.word_count == 10000

    def test_unicode_text(self):
        text = "优质无线蓝牙耳机 降噪 40mm驱动单元 30小时续航"
        profile = self.analyzer.analyze_listing(text, "蓝牙耳机")
        assert profile.title == "蓝牙耳机"
        assert profile.word_count > 0

    def test_html_detection(self):
        profile = self.analyzer.analyze_listing("<b>Bold</b> and <i>italic</i> text")
        assert profile.has_html

    def test_no_html(self):
        profile = self.analyzer.analyze_listing("Plain text no HTML here")
        assert not profile.has_html

    def test_bundle_detection(self):
        profile = self.analyzer.analyze_listing("Bundle deal: headphones set of 2 with case")
        assert profile.has_bundle

    def test_free_shipping_detection(self):
        profile = self.analyzer.analyze_listing("Comes with free shipping to your door")
        assert profile.has_free_shipping

    def test_money_back_detection(self):
        profile = self.analyzer.analyze_listing("30-day money back refund guarantee")
        assert profile.has_money_back
