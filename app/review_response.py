"""Review Response Generator.

Automatically generate professional responses to customer reviews,
handle negative review crisis management, and extract actionable insights.

Features:
- Positive review thank-you responses
- Negative review apology and solution templates
- Crisis management for 1-2 star reviews
- Keyword extraction from review text
- Sentiment analysis (basic, rule-based)
- Response tone customization (formal, casual, empathetic)
- Multi-language response support
- Bulk review response generation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ReviewSentiment(str, Enum):
    VERY_POSITIVE = "very_positive"  # 5 stars
    POSITIVE = "positive"            # 4 stars
    NEUTRAL = "neutral"              # 3 stars
    NEGATIVE = "negative"            # 2 stars
    VERY_NEGATIVE = "very_negative"  # 1 star


class ResponseTone(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    EMPATHETIC = "empathetic"
    PROFESSIONAL = "professional"


@dataclass
class Review:
    """Customer review data."""
    review_id: str
    rating: int  # 1-5
    title: str
    text: str
    reviewer_name: str = "Customer"
    verified_purchase: bool = False
    product_name: str = ""


@dataclass
class ReviewResponse:
    """Generated response to a review."""
    review_id: str
    sentiment: ReviewSentiment
    response_text: str
    tone: ResponseTone
    keywords_extracted: list[str] = field(default_factory=list)
    issues_detected: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)


# Positive review templates
POSITIVE_TEMPLATES = {
    ResponseTone.FORMAL: [
        "Thank you for your wonderful {rating}-star review, {name}! We're delighted that you're enjoying {product}. Your satisfaction is our top priority.",
        "We greatly appreciate your positive feedback, {name}. It's wonderful to hear that {product} met your expectations. Thank you for choosing us!",
    ],
    ResponseTone.CASUAL: [
        "Wow, thanks so much for the {rating} stars, {name}! 🌟 So glad you're loving {product}!",
        "Hey {name}! We're thrilled you're happy with {product}. Thanks for the awesome review!",
    ],
    ResponseTone.EMPATHETIC: [
        "Thank you from the bottom of our hearts, {name}! Knowing that {product} has made a positive difference for you truly brightens our day. ❤️",
        "Your kind words mean the world to us, {name}! We're so happy {product} is working well for you.",
    ],
    ResponseTone.PROFESSIONAL: [
        "Thank you for your {rating}-star review, {name}. We're pleased that {product} has met your needs. We look forward to serving you again.",
    ],
}

# Negative review templates
NEGATIVE_TEMPLATES = {
    ResponseTone.FORMAL: [
        "We sincerely apologize for your disappointing experience, {name}. This does not meet our quality standards. Please contact our support team at {contact} so we can make this right.",
        "Thank you for bringing this to our attention, {name}. We deeply regret that {product} did not meet your expectations. We would like to resolve this issue immediately. Please reach out to {contact}.",
    ],
    ResponseTone.EMPATHETIC: [
        "We're truly sorry to hear about your experience, {name}. 😔 This isn't the level of quality we aim for, and we'd love the chance to make it right. Please contact us at {contact}.",
        "{name}, we genuinely apologize. Your frustration is completely understandable, and we want to fix this for you. Please give us a chance to make things better by reaching out to {contact}.",
    ],
    ResponseTone.PROFESSIONAL: [
        "We apologize for the inconvenience, {name}. Please contact our customer service team at {contact} to resolve this matter promptly.",
    ],
    ResponseTone.CASUAL: [
        "Oh no, {name}! We're really sorry this didn't work out. Let's fix this - please reach out to {contact} and we'll make it right!",
    ],
}

# Crisis keywords (indicate serious issues)
CRISIS_KEYWORDS = [
    "dangerous", "unsafe", "broken", "fire hazard", "electric shock",
    "injured", "hurt", "damaged", "defective", "recall", "lawsuit",
    "scam", "fraud", "fake", "counterfeit", "never arrived", "stolen",
]

# Issue detection patterns
ISSUE_PATTERNS = {
    "quality": ["poor quality", "cheap", "broke", "flimsy", "fell apart", "defective"],
    "sizing": ["too small", "too big", "wrong size", "doesn't fit"],
    "shipping": ["late", "never arrived", "damaged in transit", "shipping took"],
    "description_mismatch": ["not as described", "looks different", "misleading"],
    "functionality": ["doesn't work", "not working", "malfunction", "stopped working"],
    "customer_service": ["rude", "no response", "ignored", "poor service"],
}


def _classify_sentiment(rating: int) -> ReviewSentiment:
    """Classify review sentiment based on rating."""
    if rating == 5:
        return ReviewSentiment.VERY_POSITIVE
    elif rating == 4:
        return ReviewSentiment.POSITIVE
    elif rating == 3:
        return ReviewSentiment.NEUTRAL
    elif rating == 2:
        return ReviewSentiment.NEGATIVE
    else:
        return ReviewSentiment.VERY_NEGATIVE


def _extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """Extract key phrases from review text."""
    # Simple extraction: find important phrases
    text_lower = text.lower()
    keywords = []

    # Check for common review phrases
    patterns = [
        r'\b(very |really |super |extremely )(\w+)',  # intensifiers
        r'\b(not |never |don\'t )(\w+)',              # negations
        r'\b(\w+) (quality|product|item)',            # adjective + noun
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            phrase = " ".join(match).strip()
            if phrase and len(phrase) > 3:
                keywords.append(phrase)

    # Add single important words
    important_words = re.findall(r'\b(excellent|amazing|perfect|great|terrible|awful|bad|poor|love|hate)\b',
                                  text_lower)
    keywords.extend(important_words)

    # Deduplicate and limit
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique[:top_n]


def _detect_issues(text: str) -> list[str]:
    """Detect specific issues mentioned in review."""
    text_lower = text.lower()
    issues = []

    for issue_type, patterns in ISSUE_PATTERNS.items():
        if any(pattern in text_lower for pattern in patterns):
            issues.append(issue_type)

    return issues


def _is_crisis_review(text: str) -> bool:
    """Check if review contains crisis keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in CRISIS_KEYWORDS)


class ReviewResponseGenerator:
    """Generate professional responses to customer reviews."""

    def __init__(self, brand_name: str = "Our Team", support_contact: str = "support@company.com"):
        self.brand_name = brand_name
        self.support_contact = support_contact

    def generate_response(
        self,
        review: Review,
        tone: ResponseTone = ResponseTone.PROFESSIONAL,
        custom_message: Optional[str] = None
    ) -> ReviewResponse:
        """Generate a response to a single review."""
        sentiment = _classify_sentiment(review.rating)
        keywords = _extract_keywords(review.text)
        issues = _detect_issues(review.text)

        # Check for crisis
        is_crisis = _is_crisis_review(review.text)

        if is_crisis:
            # Crisis response - always formal and urgent
            response_text = (
                f"Dear {review.reviewer_name}, we take your concerns very seriously. "
                f"Please contact our priority support team immediately at {self.support_contact}. "
                f"We are committed to resolving this matter urgently and ensuring your safety and satisfaction."
            )
            action_items = ["URGENT: Escalate to management", "Contact customer within 24 hours",
                           "Investigate product safety"]
        else:
            if sentiment in (ReviewSentiment.VERY_POSITIVE, ReviewSentiment.POSITIVE):
                # Positive response
                templates = POSITIVE_TEMPLATES.get(tone, POSITIVE_TEMPLATES[ResponseTone.PROFESSIONAL])
                template = templates[0]
                response_text = template.format(
                    name=review.reviewer_name,
                    rating=review.rating,
                    product=review.product_name or "our product"
                )

                if custom_message:
                    response_text += " " + custom_message

                action_items = []

            elif sentiment == ReviewSentiment.NEUTRAL:
                # Neutral response - thank + offer help
                response_text = (
                    f"Thank you for your feedback, {review.reviewer_name}. We appreciate your {review.rating}-star review. "
                    f"If there's anything we can do to improve your experience with {review.product_name or 'our product'}, "
                    f"please don't hesitate to reach out at {self.support_contact}."
                )
                action_items = ["Monitor for follow-up"]

            else:
                # Negative response
                templates = NEGATIVE_TEMPLATES.get(tone, NEGATIVE_TEMPLATES[ResponseTone.PROFESSIONAL])
                template = templates[0]
                response_text = template.format(
                    name=review.reviewer_name,
                    product=review.product_name or "the product",
                    contact=self.support_contact
                )

                if custom_message:
                    response_text += " " + custom_message

                action_items = [
                    f"Reach out to {review.reviewer_name} within 24 hours",
                    "Offer replacement or refund",
                ]
                if issues:
                    action_items.append(f"Investigate: {', '.join(issues)}")

        return ReviewResponse(
            review_id=review.review_id,
            sentiment=sentiment,
            response_text=response_text,
            tone=tone,
            keywords_extracted=keywords,
            issues_detected=issues,
            action_items=action_items
        )

    def generate_bulk_responses(
        self,
        reviews: list[Review],
        tone: ResponseTone = ResponseTone.PROFESSIONAL
    ) -> list[ReviewResponse]:
        """Generate responses for multiple reviews."""
        return [self.generate_response(r, tone) for r in reviews]

    def prioritize_reviews(
        self,
        reviews: list[Review]
    ) -> list[Review]:
        """Prioritize reviews by urgency (crisis > negative > neutral > positive)."""
        crisis = []
        negative = []
        neutral = []
        positive = []

        for review in reviews:
            if _is_crisis_review(review.text):
                crisis.append(review)
            elif review.rating <= 2:
                negative.append(review)
            elif review.rating == 3:
                neutral.append(review)
            else:
                positive.append(review)

        # Return in priority order
        return crisis + negative + neutral + positive

    def generate_summary_report(
        self,
        responses: list[ReviewResponse]
    ) -> str:
        """Generate summary report of review responses."""
        if not responses:
            return "No reviews to report."

        total = len(responses)
        sentiment_counts = {}
        for r in responses:
            sentiment_counts[r.sentiment.value] = sentiment_counts.get(r.sentiment.value, 0) + 1

        all_issues = []
        for r in responses:
            all_issues.extend(r.issues_detected)

        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        lines = [
            "═══ Review Response Report ═══",
            f"Total Reviews: {total}",
            "",
            "Sentiment Breakdown:",
        ]

        for sent, count in sorted(sentiment_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            lines.append(f"  {sent.replace('_', ' ').title()}: {count} ({pct:.1f}%)")

        if issue_counts:
            lines.append("")
            lines.append("Top Issues Detected:")
            top_issues = sorted(issue_counts.items(), key=lambda x: -x[1])[:5]
            for issue, count in top_issues:
                lines.append(f"  • {issue.replace('_', ' ').title()}: {count}")

        urgent = [r for r in responses if any("URGENT" in a for a in r.action_items)]
        if urgent:
            lines.append("")
            lines.append(f"⚠️ {len(urgent)} URGENT reviews requiring immediate attention")

        return "\n".join(lines)

    def export_responses_csv(self, responses: list[ReviewResponse]) -> str:
        """Export responses as CSV."""
        lines = ["review_id,sentiment,response,keywords,issues"]
        for r in responses:
            kw_str = "; ".join(r.keywords_extracted)
            issue_str = "; ".join(r.issues_detected)
            response_clean = r.response_text.replace('"', '""').replace('\n', ' ')
            lines.append(f'"{r.review_id}","{r.sentiment.value}","{response_clean}","{kw_str}","{issue_str}"')
        return "\n".join(lines)


def quick_response(review_text: str, rating: int, reviewer_name: str = "Customer") -> str:
    """Quick response generation (convenience function)."""
    review = Review(
        review_id="quick",
        rating=rating,
        title="",
        text=review_text,
        reviewer_name=reviewer_name
    )
    generator = ReviewResponseGenerator()
    response = generator.generate_response(review)
    return response.response_text
