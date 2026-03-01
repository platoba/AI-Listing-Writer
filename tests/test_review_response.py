"""Tests for Review Response Generator."""
import pytest
from app.review_response import (
    ReviewResponseGenerator,
    Review, ReviewResponse,
    ReviewSentiment, ResponseTone,
    _classify_sentiment, _extract_keywords, _detect_issues,
    _is_crisis_review,
    quick_response,
)


class TestSentimentClassification:
    def test_5_star_very_positive(self):
        assert _classify_sentiment(5) == ReviewSentiment.VERY_POSITIVE

    def test_4_star_positive(self):
        assert _classify_sentiment(4) == ReviewSentiment.POSITIVE

    def test_3_star_neutral(self):
        assert _classify_sentiment(3) == ReviewSentiment.NEUTRAL

    def test_2_star_negative(self):
        assert _classify_sentiment(2) == ReviewSentiment.NEGATIVE

    def test_1_star_very_negative(self):
        assert _classify_sentiment(1) == ReviewSentiment.VERY_NEGATIVE


class TestKeywordExtraction:
    def test_extract_intensifiers(self):
        keywords = _extract_keywords("This is very good and really amazing")
        assert any("very" in kw or "good" in kw for kw in keywords)

    def test_extract_sentiment_words(self):
        keywords = _extract_keywords("Excellent product, love it!")
        assert "excellent" in keywords or "love" in keywords

    def test_extract_negative_words(self):
        keywords = _extract_keywords("Terrible quality, hate this product")
        assert "terrible" in keywords or "hate" in keywords

    def test_top_n_limit(self):
        keywords = _extract_keywords("word " * 100, top_n=5)
        assert len(keywords) <= 5


class TestIssueDetection:
    def test_detect_quality_issue(self):
        issues = _detect_issues("Poor quality product broke after one use")
        assert "quality" in issues or "functionality" in issues

    def test_detect_sizing_issue(self):
        issues = _detect_issues("Product is too small, doesn't fit")
        assert "sizing" in issues

    def test_detect_shipping_issue(self):
        issues = _detect_issues("Package arrived late and damaged")
        assert "shipping" in issues

    def test_detect_description_mismatch(self):
        issues = _detect_issues("Not as described, looks different from photos")
        assert "description_mismatch" in issues

    def test_no_issues_detected(self):
        issues = _detect_issues("Great product, exactly as expected")
        assert len(issues) == 0


class TestCrisisDetection:
    def test_detect_dangerous(self):
        assert _is_crisis_review("This product is dangerous and unsafe")

    def test_detect_fire_hazard(self):
        assert _is_crisis_review("Device caught fire, major fire hazard!")

    def test_detect_injury(self):
        assert _is_crisis_review("Product broke and injured my child")

    def test_detect_fraud(self):
        assert _is_crisis_review("This is a scam, fake product")

    def test_no_crisis_in_normal_review(self):
        assert not _is_crisis_review("Product works fine, happy with it")


class TestPositiveReviewResponse:
    def test_generate_5_star_response(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 5, "Great!", "Love this product", "John")
        response = gen.generate_response(review)
        assert response.sentiment == ReviewSentiment.VERY_POSITIVE
        assert "thank" in response.response_text.lower() or "appreciate" in response.response_text.lower()

    def test_generate_4_star_response(self):
        gen = ReviewResponseGenerator()
        review = Review("R2", 4, "Good", "Nice product", "Jane")
        response = gen.generate_response(review)
        assert response.sentiment == ReviewSentiment.POSITIVE

    def test_formal_tone(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 5, "Excellent", "Great product", "Customer")
        response = gen.generate_response(review, tone=ResponseTone.FORMAL)
        # Formal tone should be polite and professional
        assert "thank" in response.response_text.lower()

    def test_casual_tone(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 5, "Awesome!", "Love it!", "John")
        response = gen.generate_response(review, tone=ResponseTone.CASUAL)
        assert response.tone == ResponseTone.CASUAL

    def test_empathetic_tone(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 5, "Perfect", "So happy", "Mary")
        response = gen.generate_response(review, tone=ResponseTone.EMPATHETIC)
        assert response.tone == ResponseTone.EMPATHETIC


class TestNegativeReviewResponse:
    def test_generate_1_star_response(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 1, "Terrible", "Worst product ever", "Angry Customer")
        response = gen.generate_response(review)
        assert response.sentiment == ReviewSentiment.VERY_NEGATIVE
        assert "apolog" in response.response_text.lower() or "sorry" in response.response_text.lower()

    def test_generate_2_star_response(self):
        gen = ReviewResponseGenerator()
        review = Review("R2", 2, "Disappointing", "Not good", "Unhappy")
        response = gen.generate_response(review)
        assert response.sentiment == ReviewSentiment.NEGATIVE

    def test_support_contact_included(self):
        gen = ReviewResponseGenerator(support_contact="help@example.com")
        review = Review("R1", 1, "Bad", "Broken product", "Customer")
        response = gen.generate_response(review)
        assert "help@example.com" in response.response_text

    def test_action_items_for_negative(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 1, "Awful", "Product broke", "Customer")
        response = gen.generate_response(review)
        assert len(response.action_items) > 0


class TestNeutralReviewResponse:
    def test_generate_3_star_response(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 3, "Okay", "It's fine", "Customer")
        response = gen.generate_response(review)
        assert response.sentiment == ReviewSentiment.NEUTRAL
        assert "thank" in response.response_text.lower()


class TestCrisisReviewResponse:
    def test_crisis_review_urgent_response(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 1, "DANGER!", "Product caught fire, very dangerous!", "Victim")
        response = gen.generate_response(review)
        assert "serious" in response.response_text.lower() or "urgent" in response.response_text.lower()
        assert any("URGENT" in action for action in response.action_items)

    def test_crisis_overrides_tone(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 1, "Unsafe", "Product is a fire hazard", "Customer")
        # Even with casual tone, crisis should get serious response
        response = gen.generate_response(review, tone=ResponseTone.CASUAL)
        assert "serious" in response.response_text.lower()


class TestKeywordAndIssueExtraction:
    def test_keywords_extracted_from_review(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 4, "Good", "Very good quality, really love it", "Customer")
        response = gen.generate_response(review)
        assert len(response.keywords_extracted) > 0

    def test_issues_detected_in_negative_review(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 2, "Poor", "Poor quality, broke after one day", "Customer")
        response = gen.generate_response(review)
        assert "quality" in response.issues_detected or "functionality" in response.issues_detected


class TestBulkResponseGeneration:
    def test_generate_bulk_responses(self):
        gen = ReviewResponseGenerator()
        reviews = [
            Review("R1", 5, "Great", "Love it", "John"),
            Review("R2", 2, "Bad", "Not good", "Jane"),
            Review("R3", 4, "Good", "Nice", "Bob"),
        ]
        responses = gen.generate_bulk_responses(reviews)
        assert len(responses) == 3
        assert all(isinstance(r, ReviewResponse) for r in responses)

    def test_bulk_with_different_tones(self):
        gen = ReviewResponseGenerator()
        reviews = [
            Review("R1", 5, "Excellent", "Amazing", "Customer1"),
            Review("R2", 4, "Good", "Nice product", "Customer2"),
        ]
        responses = gen.generate_bulk_responses(reviews, tone=ResponseTone.CASUAL)
        assert all(r.tone == ResponseTone.CASUAL for r in responses)


class TestPrioritization:
    def test_prioritize_crisis_first(self):
        gen = ReviewResponseGenerator()
        reviews = [
            Review("R1", 5, "Great", "Love it", "Happy"),
            Review("R2", 1, "Danger", "Product is dangerous!", "Victim"),
            Review("R3", 3, "Okay", "It's fine", "Neutral"),
        ]
        prioritized = gen.prioritize_reviews(reviews)
        # Crisis review should be first
        assert "dangerous" in prioritized[0].text.lower()

    def test_prioritize_negative_before_positive(self):
        gen = ReviewResponseGenerator()
        reviews = [
            Review("R1", 5, "Great", "Love it", "Happy"),
            Review("R2", 2, "Bad", "Poor quality", "Unhappy"),
            Review("R3", 4, "Good", "Nice", "Satisfied"),
        ]
        prioritized = gen.prioritize_reviews(reviews)
        # Negative (2-star) should come before positive (4, 5 star)
        negative_idx = next(i for i, r in enumerate(prioritized) if r.rating == 2)
        positive_idx = next(i for i, r in enumerate(prioritized) if r.rating == 5)
        assert negative_idx < positive_idx


class TestSummaryReport:
    def test_generate_summary_report(self):
        gen = ReviewResponseGenerator()
        responses = [
            ReviewResponse("R1", ReviewSentiment.VERY_POSITIVE, "Thanks!", ResponseTone.FORMAL),
            ReviewResponse("R2", ReviewSentiment.NEGATIVE, "Sorry!", ResponseTone.FORMAL, issues_detected=["quality"]),
        ]
        report = gen.generate_summary_report(responses)
        assert "Total Reviews: 2" in report
        assert "Sentiment Breakdown" in report

    def test_summary_includes_top_issues(self):
        gen = ReviewResponseGenerator()
        responses = [
            ReviewResponse("R1", ReviewSentiment.NEGATIVE, "Response", ResponseTone.FORMAL,
                          issues_detected=["quality", "shipping"]),
            ReviewResponse("R2", ReviewSentiment.NEGATIVE, "Response", ResponseTone.FORMAL,
                          issues_detected=["quality"]),
        ]
        report = gen.generate_summary_report(responses)
        assert "Top Issues" in report
        assert "quality" in report.lower()

    def test_summary_urgent_count(self):
        gen = ReviewResponseGenerator()
        responses = [
            ReviewResponse("R1", ReviewSentiment.VERY_NEGATIVE, "Crisis response",
                          ResponseTone.FORMAL, action_items=["URGENT: Contact customer"]),
        ]
        report = gen.generate_summary_report(responses)
        assert "URGENT" in report


class TestCSVExport:
    def test_export_responses_csv(self):
        gen = ReviewResponseGenerator()
        responses = [
            ReviewResponse("R1", ReviewSentiment.VERY_POSITIVE, "Thank you!", ResponseTone.FORMAL,
                          keywords_extracted=["great", "love"], issues_detected=[]),
        ]
        csv = gen.export_responses_csv(responses)
        assert "review_id,sentiment,response,keywords,issues" in csv
        assert "R1" in csv


class TestQuickResponse:
    def test_quick_response_5_star(self):
        response_text = quick_response("Amazing product, love it!", 5, "John")
        assert "thank" in response_text.lower() or "appreciate" in response_text.lower()

    def test_quick_response_1_star(self):
        response_text = quick_response("Terrible, broke immediately", 1, "Jane")
        assert "apolog" in response_text.lower() or "sorry" in response_text.lower()


class TestEdgeCases:
    def test_empty_review_text(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 5, "Title", "", "Customer")
        response = gen.generate_response(review)
        assert isinstance(response, ReviewResponse)

    def test_very_long_review_text(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 3, "Long", "word " * 1000, "Customer")
        response = gen.generate_response(review)
        assert isinstance(response, ReviewResponse)

    def test_special_characters_in_review(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 4, "Special™", "Product® is great™!", "Customer")
        response = gen.generate_response(review)
        assert isinstance(response, ReviewResponse)

    def test_custom_message_appended(self):
        gen = ReviewResponseGenerator()
        review = Review("R1", 5, "Great", "Love it", "Customer")
        response = gen.generate_response(review, custom_message="We'd love to see photos!")
        assert "photos" in response.response_text
