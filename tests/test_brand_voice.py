"""Tests for brand_voice module."""
import pytest
from app.brand_voice import (
    BrandVoiceProfile, BrandVoiceReport, BrandViolation,
    Tone, ViolationType,
    detect_tone, check_brand_voice, count_emojis,
    check_sentence_lengths,
    get_preset, list_presets, PRESET_PROFILES,
    TONE_INDICATORS,
)


# ── Fixtures ─────────────────────────────────────────────────

LUXURY_LISTING = """**Title** Exquisite Handcrafted Italian Leather Briefcase — Artisan Heritage Collection
**Description** Crafted by master artisans in Florence, this exquisite briefcase embodies timeless elegance.
Refined details and premium full-grain Italian leather make this piece a statement of prestige.
Each briefcase is individually numbered and comes with a certificate of authenticity.
**Bullet Points**
- Handcrafted from premium full-grain Italian leather
- Elegant brass hardware with antique finish
- Timeless design suitable for the discerning professional
"""

CASUAL_LISTING = """**Title** Super Awesome Phone Stand — You'll Love This Thing! 🎉📱
**Description** Honestly, this phone stand is just great! It's super easy to use
and totally worth every penny. Your friends are gonna be so jealous!! Grab one now!
**Bullet Points**
- Really easy to set up — basically plug and play
- Awesome adjustable angle for any position 😎
- Super sturdy, won't tip over
"""

TECHNICAL_LISTING = """**Title** USB-C Hub 7-in-1 — 4K HDMI, 100W PD, USB 3.2 Gen 2, SD/TF Card Reader
**Description** Specifications: USB-C to HDMI 2.0 (4K@60Hz), 2x USB 3.2 Gen 2 (10Gbps),
100W Power Delivery pass-through, SD/TF card interface, compatible with all USB-C devices.
Aluminum housing with thermal management. Rated for 10,000+ insertion cycles.
"""

CN_PREMIUM_LISTING = """**标题** 臻品匠心手工皮具 传承百年工艺 限量典藏款
**描述** 每一件都是匠心之作，精选顶级品质原料，尊享专属定制服务。传承百年工艺，至臻品质。
"""

CN_TRENDY_LISTING = """**标题** 这个手机壳也太酷了吧！yyds 潮人必备 🔥🔥🔥
**描述** 绝绝子！这款手机壳真的太好看了，种草安利给所有小伙伴！潮到没朋友！
"""

FORBIDDEN_WORDS_LISTING = """**Title** CHEAP Budget Phone Case — AMAZING BARGAIN DEAL!!!!
**Description** This is the BEST cheap phone case you can find. Such a bargain!
Get this incredible deal today! HURRY LIMITED TIME ONLY!! 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
"""


# ── Tone Detection ───────────────────────────────────────────

class TestDetectTone:
    def test_luxury_tone(self):
        scores = detect_tone(LUXURY_LISTING)
        assert scores.get("luxury", 0) > 0
        assert scores["luxury"] >= scores.get("casual", 0)

    def test_casual_tone(self):
        scores = detect_tone(CASUAL_LISTING)
        assert scores.get("casual", 0) > 0

    def test_technical_tone(self):
        scores = detect_tone(TECHNICAL_LISTING)
        assert scores.get("technical", 0) > 0

    def test_cn_premium_tone(self):
        scores = detect_tone(CN_PREMIUM_LISTING)
        assert scores.get("luxury", 0) > 0

    def test_cn_trendy_tone(self):
        scores = detect_tone(CN_TRENDY_LISTING)
        # Should detect playful or casual
        assert scores.get("playful", 0) > 0 or scores.get("casual", 0) > 0

    def test_empty_text(self):
        scores = detect_tone("")
        assert all(v == 0 for v in scores.values())

    def test_returns_all_tones(self):
        scores = detect_tone(LUXURY_LISTING)
        assert len(scores) == len(Tone)

    def test_scores_between_0_and_1(self):
        scores = detect_tone(CASUAL_LISTING)
        for tone, score in scores.items():
            assert 0 <= score <= 1.0, f"{tone} score {score} out of range"


# ── count_emojis ─────────────────────────────────────────────

class TestCountEmojis:
    def test_no_emojis(self):
        assert count_emojis("Hello world") == 0

    def test_single_emoji(self):
        assert count_emojis("Hello 🎉") >= 1

    def test_multiple_emojis(self):
        count = count_emojis("🔥🔥🔥 fire!")
        assert count >= 1  # At least detected some

    def test_emoji_in_text(self):
        count = count_emojis("Great product 😎 love it 💯")
        assert count >= 1


# ── check_sentence_lengths ───────────────────────────────────

class TestCheckSentenceLengths:
    def test_normal_sentences(self):
        violations = check_sentence_lengths(
            "This is fine. So is this.", max_len=30, min_len=2
        )
        assert len(violations) == 0

    def test_long_sentence(self):
        long = " ".join(["word"] * 35) + "."
        violations = check_sentence_lengths(long, max_len=30, min_len=2)
        assert len(violations) > 0
        assert violations[0].violation_type == ViolationType.STYLE_VIOLATION

    def test_short_sentence(self):
        violations = check_sentence_lengths("Ok. Good.", max_len=30, min_len=3)
        assert any("short" in v.message.lower() for v in violations)

    def test_empty_text(self):
        violations = check_sentence_lengths("", max_len=30, min_len=2)
        assert len(violations) == 0


# ── BrandVoiceProfile ───────────────────────────────────────

class TestBrandVoiceProfile:
    def test_create_profile(self):
        profile = BrandVoiceProfile(
            name="Test Brand",
            tone=Tone.PROFESSIONAL,
            preferred_words=["quality", "reliable"],
            forbidden_words=["cheap"],
        )
        assert profile.name == "Test Brand"
        assert profile.tone == Tone.PROFESSIONAL

    def test_to_dict(self):
        profile = BrandVoiceProfile(name="Test", tone=Tone.CASUAL)
        d = profile.to_dict()
        assert d["name"] == "Test"
        assert d["tone"] == "casual"

    def test_from_dict(self):
        data = {"name": "Rebuilt", "tone": "luxury", "preferred_words": ["exquisite"]}
        profile = BrandVoiceProfile.from_dict(data)
        assert profile.name == "Rebuilt"
        assert profile.tone == Tone.LUXURY
        assert "exquisite" in profile.preferred_words

    def test_from_dict_defaults(self):
        profile = BrandVoiceProfile.from_dict({})
        assert profile.name == "Untitled"
        assert profile.tone == Tone.PROFESSIONAL


# ── check_brand_voice ────────────────────────────────────────

class TestCheckBrandVoice:
    def test_luxury_pass(self):
        profile = get_preset("luxury_brand")
        report = check_brand_voice(LUXURY_LISTING, profile)
        # Should mostly pass — it's a luxury-style listing
        assert report.compliance_score > 50
        assert len(report.preferred_words_used) > 0

    def test_forbidden_words_detected(self):
        profile = get_preset("luxury_brand")
        report = check_brand_voice(FORBIDDEN_WORDS_LISTING, profile)
        forbidden_violations = [v for v in report.violations
                                if v.violation_type == ViolationType.FORBIDDEN_WORD]
        assert len(forbidden_violations) > 0
        assert report.compliance_score < 100

    def test_emoji_violation(self):
        profile = get_preset("luxury_brand")  # No emojis allowed
        report = check_brand_voice(CASUAL_LISTING, profile)
        emoji_violations = [v for v in report.violations
                            if v.violation_type == ViolationType.EMOJI_VIOLATION]
        assert len(emoji_violations) > 0

    def test_all_caps_violation(self):
        profile = BrandVoiceProfile(
            name="No Caps",
            tone=Tone.PROFESSIONAL,
            allow_all_caps=False,
        )
        report = check_brand_voice(FORBIDDEN_WORDS_LISTING, profile)
        style_violations = [v for v in report.violations
                            if v.violation_type == ViolationType.STYLE_VIOLATION]
        # Should detect CHEAP, AMAZING, BARGAIN, BEST, HURRY, etc.
        assert len(style_violations) > 0

    def test_exclamation_marks(self):
        profile = BrandVoiceProfile(
            name="Calm Brand",
            tone=Tone.PROFESSIONAL,
            max_exclamation_marks=1,
        )
        report = check_brand_voice(FORBIDDEN_WORDS_LISTING, profile)
        excl_violations = [v for v in report.violations
                           if "exclamation" in v.message.lower()]
        assert len(excl_violations) > 0

    def test_required_phrases_missing(self):
        profile = BrandVoiceProfile(
            name="Test",
            tone=Tone.PROFESSIONAL,
            required_phrases=["money-back guarantee", "free shipping"],
        )
        report = check_brand_voice(LUXURY_LISTING, profile)
        assert len(report.required_phrases_missing) == 2

    def test_required_phrases_found(self):
        profile = BrandVoiceProfile(
            name="Test",
            tone=Tone.PROFESSIONAL,
            required_phrases=["handcrafted"],
        )
        report = check_brand_voice(LUXURY_LISTING, profile)
        assert "handcrafted" in report.required_phrases_found

    def test_preferred_words_tracking(self):
        profile = BrandVoiceProfile(
            name="Test",
            tone=Tone.LUXURY,
            preferred_words=["exquisite", "handcrafted", "unicorn", "dragon"],
        )
        report = check_brand_voice(LUXURY_LISTING, profile)
        assert "exquisite" in report.preferred_words_used
        assert "unicorn" in report.preferred_words_missing

    def test_tone_scores_populated(self):
        profile = get_preset("luxury_brand")
        report = check_brand_voice(LUXURY_LISTING, profile)
        assert len(report.tone_scores) > 0

    def test_tech_listing_against_tech_profile(self):
        profile = get_preset("tech_brand")
        report = check_brand_voice(TECHNICAL_LISTING, profile)
        assert report.compliance_score > 50

    def test_casual_listing_against_casual_profile(self):
        profile = get_preset("casual_brand")
        report = check_brand_voice(CASUAL_LISTING, profile)
        assert report.compliance_score > 50

    def test_cn_premium_listing(self):
        profile = get_preset("cn_premium")
        report = check_brand_voice(CN_PREMIUM_LISTING, profile)
        assert report.compliance_score > 50

    def test_cn_trendy_listing(self):
        profile = get_preset("cn_trendy")
        report = check_brand_voice(CN_TRENDY_LISTING, profile)
        assert len(report.preferred_words_used) > 0

    def test_empty_text(self):
        profile = get_preset("luxury_brand")
        report = check_brand_voice("", profile)
        assert isinstance(report, BrandVoiceReport)


# ── BrandVoiceReport ─────────────────────────────────────────

class TestBrandVoiceReport:
    def test_summary_not_empty(self):
        profile = get_preset("luxury_brand")
        report = check_brand_voice(LUXURY_LISTING, profile)
        summary = report.summary()
        assert len(summary) > 50
        assert "Brand Voice Report" in summary

    def test_passed_property(self):
        report = BrandVoiceReport(profile_name="test")
        assert report.passed is True  # No violations

    def test_failed_property(self):
        report = BrandVoiceReport(
            profile_name="test",
            violations=[BrandViolation(
                violation_type=ViolationType.FORBIDDEN_WORD,
                severity="error",
                message="test",
            )],
        )
        assert report.passed is False

    def test_error_count(self):
        report = BrandVoiceReport(
            profile_name="test",
            violations=[
                BrandViolation(ViolationType.FORBIDDEN_WORD, "error", "msg1"),
                BrandViolation(ViolationType.STYLE_VIOLATION, "warning", "msg2"),
                BrandViolation(ViolationType.FORBIDDEN_WORD, "error", "msg3"),
            ],
        )
        assert report.error_count == 2
        assert report.warning_count == 1


# ── Presets ──────────────────────────────────────────────────

class TestPresets:
    def test_list_presets(self):
        presets = list_presets()
        assert len(presets) >= 5
        assert "luxury_brand" in presets
        assert "tech_brand" in presets
        assert "casual_brand" in presets

    def test_get_preset(self):
        profile = get_preset("luxury_brand")
        assert profile is not None
        assert profile.tone == Tone.LUXURY

    def test_get_unknown_preset(self):
        profile = get_preset("nonexistent")
        assert profile is None

    def test_all_presets_valid(self):
        for name in list_presets():
            profile = get_preset(name)
            assert profile is not None
            assert profile.name != ""
            assert isinstance(profile.tone, Tone)

    def test_cn_presets_exist(self):
        assert "cn_premium" in list_presets()
        assert "cn_trendy" in list_presets()


# ── Tone Indicators Coverage ─────────────────────────────────

class TestToneIndicators:
    def test_all_tones_have_indicators(self):
        for tone in Tone:
            assert tone in TONE_INDICATORS, f"Missing indicators for {tone}"

    def test_indicators_have_en_and_cn(self):
        for tone, langs in TONE_INDICATORS.items():
            assert "en" in langs, f"{tone} missing English indicators"
            assert "cn" in langs, f"{tone} missing Chinese indicators"
            assert len(langs["en"]) >= 5, f"{tone} has too few English indicators"
            assert len(langs["cn"]) >= 5, f"{tone} has too few Chinese indicators"
