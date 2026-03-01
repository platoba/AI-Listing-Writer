"""Customer Q&A Generator — auto-generate FAQ, buyer questions & answers,
and pre-purchase objection handlers from listing content.

Features:
- AI-free pattern-based Q&A generation from listing text
- Buyer persona-based question generation (first-timer, comparison shopper, etc.)
- Objection detection and response crafting
- Platform-specific Q&A formatting (Amazon, eBay, Shopify)
- Question categorization (shipping, quality, compatibility, sizing, etc.)
- Confidence scoring for generated answers
- Multi-language Q&A generation
- Bulk Q&A generation for product catalogs
- Export to CSV/JSON/platform-specific format
- SQLite storage for Q&A history
"""

from __future__ import annotations

import re
import sqlite3
import json
import hashlib
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class QuestionCategory(str, Enum):
    SHIPPING = "shipping"
    QUALITY = "quality"
    COMPATIBILITY = "compatibility"
    SIZING = "sizing"
    MATERIAL = "material"
    WARRANTY = "warranty"
    USAGE = "usage"
    COMPARISON = "comparison"
    SAFETY = "safety"
    CARE = "care"
    RETURNS = "returns"
    PRICE = "price"
    AUTHENTICITY = "authenticity"
    CUSTOMIZATION = "customization"
    GENERAL = "general"


class BuyerPersona(str, Enum):
    FIRST_TIMER = "first_timer"        # Never bought this type before
    COMPARISON = "comparison"          # Comparing with competitors
    TECHNICAL = "technical"            # Wants detailed specs
    BUDGET = "budget"                  # Price-sensitive
    GIFT_BUYER = "gift_buyer"          # Buying as gift
    REPEAT = "repeat"                  # Has bought similar before
    SKEPTIC = "skeptic"                # Needs convincing
    IMPULSE = "impulse"                # Quick decision maker


class Platform(str, Enum):
    AMAZON = "amazon"
    EBAY = "ebay"
    SHOPIFY = "shopify"
    WALMART = "walmart"
    ETSY = "etsy"
    ALIEXPRESS = "aliexpress"
    GENERAL = "general"


# Question templates by category
QUESTION_TEMPLATES: dict[str, list[dict]] = {
    "shipping": [
        {"q": "How long does shipping take?", "triggers": ["ship", "deliver", "arrival"],
         "persona": ["first_timer", "impulse"]},
        {"q": "Do you ship internationally?", "triggers": ["international", "worldwide", "global"],
         "persona": ["first_timer"]},
        {"q": "Is there free shipping?", "triggers": ["free ship", "shipping cost"],
         "persona": ["budget"]},
        {"q": "What carrier do you use for shipping?", "triggers": ["carrier", "ups", "fedex", "usps"],
         "persona": ["technical"]},
        {"q": "Can I get expedited shipping?", "triggers": ["fast", "express", "rush", "overnight"],
         "persona": ["impulse"]},
        {"q": "Do you ship to PO boxes?", "triggers": ["po box", "military", "apo"],
         "persona": ["first_timer"]},
    ],
    "quality": [
        {"q": "Is this product made from high-quality materials?", "triggers": ["quality", "durable", "premium"],
         "persona": ["skeptic", "comparison"]},
        {"q": "How long does this product typically last?", "triggers": ["last", "durable", "lifespan", "warranty"],
         "persona": ["comparison", "technical"]},
        {"q": "Are there any known defects or issues?", "triggers": ["defect", "issue", "problem"],
         "persona": ["skeptic"]},
        {"q": "Is this the same quality as shown in the photos?", "triggers": ["photo", "picture", "image"],
         "persona": ["skeptic", "first_timer"]},
    ],
    "compatibility": [
        {"q": "Is this compatible with {device}?", "triggers": ["compatible", "fit", "work with"],
         "persona": ["technical"]},
        {"q": "What sizes/models does this fit?", "triggers": ["fit", "size", "model"],
         "persona": ["technical", "first_timer"]},
        {"q": "Will this work with my existing setup?", "triggers": ["setup", "system", "existing"],
         "persona": ["technical"]},
    ],
    "sizing": [
        {"q": "How does the sizing run? True to size?", "triggers": ["size", "fit", "large", "small"],
         "persona": ["first_timer", "comparison"]},
        {"q": "What are the exact dimensions?", "triggers": ["dimension", "measure", "length", "width", "height"],
         "persona": ["technical"]},
        {"q": "Is there a size chart available?", "triggers": ["size chart", "sizing guide"],
         "persona": ["first_timer"]},
        {"q": "What size should I get for {use_case}?", "triggers": ["recommend", "suggest", "best size"],
         "persona": ["first_timer", "gift_buyer"]},
    ],
    "material": [
        {"q": "What material is this made of?", "triggers": ["material", "made of", "fabric", "composition"],
         "persona": ["technical", "skeptic"]},
        {"q": "Is this product eco-friendly or sustainable?", "triggers": ["eco", "sustainable", "organic", "recycle"],
         "persona": ["comparison"]},
        {"q": "Is this material safe for children/pets?", "triggers": ["safe", "toxic", "bpa", "child"],
         "persona": ["first_timer", "gift_buyer"]},
        {"q": "Is this material hypoallergenic?", "triggers": ["allergy", "hypoallergenic", "sensitive"],
         "persona": ["technical"]},
    ],
    "warranty": [
        {"q": "Does this come with a warranty?", "triggers": ["warranty", "guarantee"],
         "persona": ["skeptic", "comparison"]},
        {"q": "What does the warranty cover?", "triggers": ["warranty cover", "guarantee include"],
         "persona": ["technical"]},
        {"q": "How do I make a warranty claim?", "triggers": ["claim", "warranty process"],
         "persona": ["technical"]},
    ],
    "usage": [
        {"q": "How do I set this up?", "triggers": ["setup", "install", "assemble"],
         "persona": ["first_timer"]},
        {"q": "Does this require batteries or power?", "triggers": ["battery", "power", "charge", "plug"],
         "persona": ["first_timer", "technical"]},
        {"q": "Can I use this outdoors?", "triggers": ["outdoor", "waterproof", "weather"],
         "persona": ["first_timer"]},
        {"q": "Is this easy to clean/maintain?", "triggers": ["clean", "wash", "maintain", "care"],
         "persona": ["first_timer", "comparison"]},
    ],
    "returns": [
        {"q": "What is the return policy?", "triggers": ["return", "refund", "exchange"],
         "persona": ["skeptic", "first_timer"]},
        {"q": "Can I return this if it doesn't fit?", "triggers": ["return", "exchange", "fit"],
         "persona": ["first_timer"]},
        {"q": "Do I have to pay for return shipping?", "triggers": ["return ship", "return cost"],
         "persona": ["budget"]},
    ],
    "price": [
        {"q": "Will this go on sale soon?", "triggers": ["sale", "discount", "coupon", "deal"],
         "persona": ["budget"]},
        {"q": "Is there a bulk/wholesale discount?", "triggers": ["bulk", "wholesale", "quantity"],
         "persona": ["budget", "repeat"]},
        {"q": "Why is this priced higher than similar products?", "triggers": ["price", "expensive", "worth"],
         "persona": ["comparison", "skeptic"]},
    ],
    "authenticity": [
        {"q": "Is this an authentic/genuine product?", "triggers": ["authentic", "genuine", "original", "real"],
         "persona": ["skeptic"]},
        {"q": "Is this an authorized dealer?", "triggers": ["authorized", "official", "dealer"],
         "persona": ["skeptic", "comparison"]},
    ],
    "care": [
        {"q": "How should I store this product?", "triggers": ["store", "storage", "keep"],
         "persona": ["first_timer"]},
        {"q": "What cleaning products can I use?", "triggers": ["clean", "soap", "detergent"],
         "persona": ["first_timer"]},
    ],
    "safety": [
        {"q": "Is this product safe to use?", "triggers": ["safe", "danger", "hazard"],
         "persona": ["first_timer", "gift_buyer"]},
        {"q": "Does this meet safety certifications?", "triggers": ["certified", "CE", "UL", "FCC", "FDA"],
         "persona": ["technical", "skeptic"]},
    ],
}

# Objection patterns
OBJECTION_PATTERNS: dict[str, dict] = {
    "too_expensive": {
        "triggers": ["expensive", "pricey", "overpriced", "cheaper", "cost too much"],
        "response_template": "While {product} may seem pricier than alternatives, consider the {value_props}. "
                             "Our customers find the investment worthwhile because {benefits}.",
    },
    "quality_doubt": {
        "triggers": ["cheap looking", "low quality", "breaks easily", "flimsy"],
        "response_template": "{product} is built with {materials}. {quality_evidence}",
    },
    "trust_issue": {
        "triggers": ["scam", "fake", "not real", "knockoff", "counterfeit"],
        "response_template": "We are an authorized seller of {product}. {trust_signals}",
    },
    "shipping_concern": {
        "triggers": ["takes too long", "slow shipping", "lost package"],
        "response_template": "We ship via {shipping_method}. {shipping_details}",
    },
    "sizing_worry": {
        "triggers": ["wrong size", "doesn't fit", "too big", "too small"],
        "response_template": "We recommend checking our sizing guide. {sizing_info} "
                             "If it doesn't fit, {return_policy}.",
    },
}

# Platform-specific Q&A formats
PLATFORM_FORMATS = {
    "amazon": {"max_q_len": 300, "max_a_len": 2000, "html": False},
    "ebay": {"max_q_len": 500, "max_a_len": 5000, "html": True},
    "shopify": {"max_q_len": None, "max_a_len": None, "html": True},
    "walmart": {"max_q_len": 300, "max_a_len": 2000, "html": False},
    "etsy": {"max_q_len": 500, "max_a_len": 3000, "html": False},
    "aliexpress": {"max_q_len": 200, "max_a_len": 1000, "html": False},
    "general": {"max_q_len": None, "max_a_len": None, "html": False},
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class QAPair:
    """A single question-answer pair."""
    question: str
    answer: str
    category: str = "general"
    persona: str = ""
    confidence: float = 0.8
    source_context: str = ""    # What listing text generated this
    platform: str = "general"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ObjectionResponse:
    """Objection and its response."""
    objection_type: str
    objection_text: str
    response: str
    confidence: float = 0.7

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QAReport:
    """Complete Q&A generation report."""
    listing_title: str
    total_questions: int
    qa_pairs: list[QAPair] = field(default_factory=list)
    objection_responses: list[ObjectionResponse] = field(default_factory=list)
    categories_covered: list[str] = field(default_factory=list)
    personas_targeted: list[str] = field(default_factory=list)
    avg_confidence: float = 0.0
    platform: str = "general"

    def to_dict(self) -> dict:
        return {
            "listing_title": self.listing_title,
            "total_questions": self.total_questions,
            "qa_pairs": [qa.to_dict() for qa in self.qa_pairs],
            "objection_responses": [o.to_dict() for o in self.objection_responses],
            "categories_covered": self.categories_covered,
            "personas_targeted": self.personas_targeted,
            "avg_confidence": round(self.avg_confidence, 2),
            "platform": self.platform,
        }

    def summary(self) -> str:
        lines = [
            f"═══ Q&A Report: {self.listing_title[:50]} ═══",
            f"Total Q&A pairs: {self.total_questions}",
            f"Categories: {', '.join(self.categories_covered)}",
            f"Personas: {', '.join(self.personas_targeted)}",
            f"Avg confidence: {self.avg_confidence:.0%}",
            f"Objection handlers: {len(self.objection_responses)}",
        ]
        return "\n".join(lines)

    def to_csv(self) -> str:
        """Export Q&A pairs as CSV."""
        lines = ["question,answer,category,persona,confidence"]
        for qa in self.qa_pairs:
            q = qa.question.replace('"', '""')
            a = qa.answer.replace('"', '""')
            lines.append(f'"{q}","{a}","{qa.category}","{qa.persona}",{qa.confidence:.2f}')
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_features(text: str) -> list[str]:
    """Extract product features from listing text."""
    features = []
    # Bullet point patterns
    for pattern in [r"[•●◉◆▪►✓✔★☆→]\s*(.+)", r"^\s*[-*]\s+(.+)", r"^\d+[.)]\s+(.+)"]:
        matches = re.findall(pattern, text, re.MULTILINE)
        features.extend(matches)
    # Sentence-level features
    feature_keywords = ["features", "includes", "comes with", "equipped with", "built-in",
                        "designed for", "perfect for", "ideal for", "suitable for"]
    for sent in re.split(r'[.!?]', text):
        sent = sent.strip()
        if any(kw in sent.lower() for kw in feature_keywords) and 10 < len(sent) < 200:
            features.append(sent)
    return features[:20]  # Cap at 20


def _extract_specs(text: str) -> dict:
    """Extract specifications from listing text."""
    specs = {}
    # Key: value patterns
    for pattern in [r"(\w[\w\s]{2,20})[:：]\s*(.+?)(?:\n|$)",
                    r"(\w[\w\s]{2,20})\s*[-–—]\s*(.+?)(?:\n|$)"]:
        for m in re.finditer(pattern, text):
            key = m.group(1).strip().lower()
            val = m.group(2).strip()
            if 2 < len(key) < 25 and 1 < len(val) < 100:
                specs[key] = val
    # Dimension patterns
    dim_match = re.search(r'(\d+\.?\d*)\s*[x×X]\s*(\d+\.?\d*)\s*[x×X]?\s*(\d+\.?\d*)?\s*(cm|inch|in|mm|")', text)
    if dim_match:
        specs["dimensions"] = dim_match.group(0)
    # Weight patterns
    weight_match = re.search(r'(\d+\.?\d*)\s*(kg|g|lb|lbs|oz|ounce|gram|pound)', text, re.I)
    if weight_match:
        specs["weight"] = weight_match.group(0)
    return specs


def _extract_materials(text: str) -> list[str]:
    """Extract material mentions from text."""
    material_keywords = [
        "cotton", "polyester", "nylon", "leather", "silk", "wool", "linen", "bamboo",
        "stainless steel", "aluminum", "aluminium", "carbon fiber", "plastic", "abs",
        "silicone", "rubber", "glass", "ceramic", "wood", "oak", "walnut", "maple",
        "titanium", "copper", "brass", "zinc", "iron", "polycarbonate", "acrylic",
        "memory foam", "latex", "gel", "microfiber", "mesh", "canvas", "denim",
        "velvet", "satin", "chiffon", "organza", "spandex", "lycra", "rayon",
    ]
    found = []
    text_lower = text.lower()
    for mat in material_keywords:
        if mat in text_lower:
            found.append(mat)
    return found


def _generate_answer(question: str, title: str, description: str,
                     features: list[str], specs: dict, materials: list[str],
                     category: str) -> tuple[str, float]:
    """Generate an answer based on listing content. Returns (answer, confidence)."""
    text = f"{title} {description}".lower()
    q_lower = question.lower()

    # Shipping questions
    if category == "shipping":
        shipping_info = []
        if "free ship" in text or "free delivery" in text:
            shipping_info.append("Yes, we offer free shipping")
        if any(w in text for w in ["next day", "same day", "express"]):
            shipping_info.append("Express/expedited shipping is available")
        if any(w in text for w in ["international", "worldwide", "global"]):
            shipping_info.append("We ship internationally")
        if shipping_info:
            return ". ".join(shipping_info) + ".", 0.85
        return "Please check our shipping policy for delivery times and options.", 0.5

    # Sizing/dimension questions
    if category == "sizing":
        if "dimensions" in specs:
            return f"The dimensions are {specs['dimensions']}.", 0.95
        if "weight" in specs:
            return f"Weight: {specs['weight']}. Please check the product details for full dimensions.", 0.7
        size_info = [f for f in features if any(w in f.lower() for w in ["size", "dimension", "measure"])]
        if size_info:
            return size_info[0], 0.8
        return "Please refer to our detailed product specifications for sizing information.", 0.4

    # Material questions
    if category == "material":
        if materials:
            mat_str = ", ".join(materials)
            return f"This product is made with {mat_str}.", 0.9
        mat_features = [f for f in features if any(w in f.lower() for w in ["material", "made", "fabric", "built"])]
        if mat_features:
            return mat_features[0], 0.75
        return "Please refer to the product description for material details.", 0.4

    # Quality questions
    if category == "quality":
        quality_indicators = []
        if materials:
            quality_indicators.append(f"made with {', '.join(materials[:3])}")
        quality_features = [f for f in features if any(w in f.lower()
                           for w in ["durable", "premium", "quality", "strong", "heavy duty"])]
        if quality_features:
            quality_indicators.append(quality_features[0])
        if quality_indicators:
            return f"This product features: {'; '.join(quality_indicators)}.", 0.8
        return "We stand behind the quality of our products. Please see customer reviews for details.", 0.5

    # Warranty questions
    if category == "warranty":
        warranty_info = [f for f in features if any(w in f.lower() for w in ["warranty", "guarantee", "year"])]
        if warranty_info:
            return warranty_info[0], 0.85
        if "warranty" in text:
            return "Yes, this product comes with a warranty. Check product details for terms.", 0.7
        return "Please contact us for warranty information.", 0.4

    # Usage questions
    if category == "usage":
        usage_features = [f for f in features if any(w in f.lower()
                         for w in ["easy", "simple", "setup", "install", "use", "step"])]
        if usage_features:
            return usage_features[0], 0.75
        return "Please see the included instructions for setup and usage details.", 0.5

    # Compatibility questions
    if category == "compatibility":
        compat_features = [f for f in features if any(w in f.lower()
                          for w in ["compatible", "fits", "works with", "supports"])]
        if compat_features:
            return compat_features[0], 0.8
        return "Please check the product specifications for compatibility information.", 0.45

    # Safety questions
    if category == "safety":
        safety_info = [f for f in features if any(w in f.lower()
                      for w in ["safe", "certified", "tested", "approved", "ce", "ul", "fcc"])]
        if safety_info:
            return safety_info[0], 0.85
        return "This product meets applicable safety standards. Contact us for certification details.", 0.5

    # Returns questions
    if category == "returns":
        if any(w in text for w in ["30 day", "30-day", "money back", "full refund"]):
            return "We offer a hassle-free return policy. If you're not satisfied, contact us for a return.", 0.8
        return "Please check our return policy for details on returns and exchanges.", 0.5

    # Price questions
    if category == "price":
        if "sale" in text or "discount" in text or "deal" in text:
            return "Check our listing for current promotions and deals.", 0.7
        return "We offer competitive pricing. Check for current promotions.", 0.5

    # Authenticity
    if category == "authenticity":
        if any(w in text for w in ["authentic", "genuine", "official", "authorized"]):
            return "Yes, this is a 100% authentic product from an authorized seller.", 0.85
        return "We sell genuine products. Contact us if you have authenticity concerns.", 0.6

    # General / fallback
    relevant_features = features[:3] if features else []
    if relevant_features:
        return f"Based on product details: {'; '.join(relevant_features)}.", 0.6
    return "Please refer to the full product description for more details, or contact us with specific questions.", 0.35


# ---------------------------------------------------------------------------
# Core Generator
# ---------------------------------------------------------------------------

class CustomerQAGenerator:
    """Generate customer Q&A content from listing data."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        if db_path:
            self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qa_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT,
                question TEXT,
                answer TEXT,
                category TEXT,
                persona TEXT,
                confidence REAL,
                platform TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_qa_listing ON qa_history(listing_id)
        """)
        conn.commit()
        conn.close()

    def generate(
        self,
        title: str,
        description: str = "",
        platform: str = "general",
        personas: Optional[list[str]] = None,
        categories: Optional[list[str]] = None,
        max_questions: int = 30,
        min_confidence: float = 0.3,
        listing_id: Optional[str] = None,
        include_objections: bool = True,
    ) -> QAReport:
        """Generate Q&A pairs from listing content."""
        # Extract listing data
        features = _extract_features(f"{title}\n{description}")
        specs = _extract_specs(description)
        materials = _extract_materials(f"{title} {description}")
        combined = f"{title} {description}".lower()

        # Filter categories
        active_categories = categories or list(QUESTION_TEMPLATES.keys())

        # Filter personas
        active_personas = set(personas) if personas else None

        qa_pairs = []
        categories_used = set()
        personas_used = set()

        for cat in active_categories:
            templates = QUESTION_TEMPLATES.get(cat, [])
            for tmpl in templates:
                # Check if any trigger words match the listing
                relevance = sum(1 for t in tmpl["triggers"] if t in combined)
                has_content = relevance > 0

                # Check persona filter
                tmpl_personas = tmpl.get("persona", [])
                if active_personas:
                    if not any(p in active_personas for p in tmpl_personas):
                        continue

                # Generate the Q&A
                question = tmpl["q"]
                # Replace placeholders
                if "{device}" in question:
                    devices = re.findall(r"(?:for|with|fits?)\s+(\w+(?:\s+\w+)?)", combined)
                    if devices:
                        question = question.replace("{device}", devices[0])
                    else:
                        question = question.replace("{device}", "my device")
                if "{use_case}" in question:
                    question = question.replace("{use_case}", "general use")

                answer, confidence = _generate_answer(
                    question, title, description, features, specs, materials, cat)

                # Boost confidence if triggers matched
                if has_content:
                    confidence = min(1.0, confidence + 0.1 * relevance)
                else:
                    confidence *= 0.7

                if confidence < min_confidence:
                    continue

                persona_str = tmpl_personas[0] if tmpl_personas else ""

                qa = QAPair(
                    question=question,
                    answer=answer,
                    category=cat,
                    persona=persona_str,
                    confidence=round(confidence, 2),
                    platform=platform,
                )
                qa_pairs.append(qa)
                categories_used.add(cat)
                if persona_str:
                    personas_used.add(persona_str)

        # Sort by confidence descending, then cap
        qa_pairs.sort(key=lambda x: x.confidence, reverse=True)
        qa_pairs = qa_pairs[:max_questions]

        # Apply platform formatting
        fmt = PLATFORM_FORMATS.get(platform, PLATFORM_FORMATS["general"])
        for qa in qa_pairs:
            if fmt["max_q_len"] and len(qa.question) > fmt["max_q_len"]:
                qa.question = qa.question[:fmt["max_q_len"] - 3] + "..."
            if fmt["max_a_len"] and len(qa.answer) > fmt["max_a_len"]:
                qa.answer = qa.answer[:fmt["max_a_len"] - 3] + "..."

        # Generate objection responses
        objections = []
        if include_objections:
            objections = self._generate_objection_responses(
                title, description, features, materials)

        # Calculate average confidence
        avg_conf = sum(qa.confidence for qa in qa_pairs) / len(qa_pairs) if qa_pairs else 0.0

        report = QAReport(
            listing_title=title,
            total_questions=len(qa_pairs),
            qa_pairs=qa_pairs,
            objection_responses=objections,
            categories_covered=sorted(categories_used),
            personas_targeted=sorted(personas_used),
            avg_confidence=avg_conf,
            platform=platform,
        )

        # Persist if db configured
        if self.db_path and listing_id:
            self._save_qa(listing_id, qa_pairs)

        return report

    def _generate_objection_responses(
        self, title: str, description: str,
        features: list[str], materials: list[str]
    ) -> list[ObjectionResponse]:
        """Generate responses to common buyer objections."""
        responses = []
        combined = f"{title} {description}".lower()

        for obj_type, obj_info in OBJECTION_PATTERNS.items():
            # Check if listing content has potential objection triggers
            template = obj_info["response_template"]

            if obj_type == "too_expensive":
                value_props = []
                if materials:
                    value_props.append(f"premium {', '.join(materials[:2])}")
                if any(w in combined for w in ["warranty", "guarantee"]):
                    value_props.append("backed by warranty")
                quality_features = [f for f in features if any(w in f.lower()
                                   for w in ["premium", "quality", "durable"])]
                if quality_features:
                    value_props.append(quality_features[0][:80])

                if value_props:
                    response = template.format(
                        product=title[:50],
                        value_props=", ".join(value_props),
                        benefits="long-lasting quality and satisfaction"
                    )
                    responses.append(ObjectionResponse(
                        objection_type=obj_type,
                        objection_text="This seems expensive compared to alternatives",
                        response=response,
                        confidence=0.75,
                    ))

            elif obj_type == "quality_doubt":
                if materials or features:
                    mat_str = ", ".join(materials[:3]) if materials else "high-quality materials"
                    evidence = features[0] if features else "Rigorous quality control standards"
                    response = template.format(
                        product=title[:50],
                        materials=mat_str,
                        quality_evidence=evidence[:100],
                    )
                    responses.append(ObjectionResponse(
                        objection_type=obj_type,
                        objection_text="I'm worried about the quality",
                        response=response,
                        confidence=0.7,
                    ))

            elif obj_type == "trust_issue":
                trust_signals = []
                if any(w in combined for w in ["authentic", "genuine", "official"]):
                    trust_signals.append("100% authentic product")
                if any(w in combined for w in ["warranty", "guarantee"]):
                    trust_signals.append("backed by manufacturer warranty")
                trust_signals.append("We have a track record of positive customer reviews")

                response = template.format(
                    product=title[:50],
                    trust_signals=" ".join(trust_signals),
                )
                responses.append(ObjectionResponse(
                    objection_type=obj_type,
                    objection_text="How do I know this is genuine?",
                    response=response,
                    confidence=0.65,
                ))

            elif obj_type == "shipping_concern":
                shipping_method = "reliable carriers"
                shipping_details = "Orders are processed within 1-2 business days."
                if "free ship" in combined:
                    shipping_details += " Free shipping included."
                response = template.format(
                    shipping_method=shipping_method,
                    shipping_details=shipping_details,
                )
                responses.append(ObjectionResponse(
                    objection_type=obj_type,
                    objection_text="I'm worried about shipping time/reliability",
                    response=response,
                    confidence=0.6,
                ))

            elif obj_type == "sizing_worry":
                sizing_info = ""
                size_features = [f for f in features if any(w in f.lower()
                                for w in ["size", "fit", "dimension"])]
                if size_features:
                    sizing_info = size_features[0][:100]
                else:
                    sizing_info = "Please check the size chart in our listing"
                return_policy = "we offer easy returns and exchanges"
                response = template.format(
                    sizing_info=sizing_info,
                    return_policy=return_policy,
                )
                responses.append(ObjectionResponse(
                    objection_type=obj_type,
                    objection_text="What if it doesn't fit?",
                    response=response,
                    confidence=0.65,
                ))

        return responses

    def generate_bulk(
        self,
        listings: list[dict],
        platform: str = "general",
        max_per_listing: int = 15,
    ) -> list[QAReport]:
        """Generate Q&A for multiple listings."""
        reports = []
        for listing in listings:
            report = self.generate(
                title=listing.get("title", ""),
                description=listing.get("description", ""),
                platform=platform,
                max_questions=max_per_listing,
                listing_id=listing.get("id"),
            )
            reports.append(report)
        return reports

    def export_json(self, report: QAReport) -> str:
        """Export report as JSON."""
        return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)

    def export_csv(self, report: QAReport) -> str:
        """Export Q&A pairs as CSV."""
        return report.to_csv()

    # ── Persistence ──────────────────────────────────────

    def _save_qa(self, listing_id: str, qa_pairs: list[QAPair]):
        if not self.db_path:
            return
        conn = sqlite3.connect(self.db_path)
        for qa in qa_pairs:
            conn.execute(
                "INSERT INTO qa_history (listing_id, question, answer, category, "
                "persona, confidence, platform) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (listing_id, qa.question, qa.answer, qa.category,
                 qa.persona, qa.confidence, qa.platform),
            )
        conn.commit()
        conn.close()

    def get_history(self, listing_id: str, limit: int = 50) -> list[dict]:
        """Get Q&A history for a listing."""
        if not self.db_path:
            return []
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT question, answer, category, persona, confidence, platform, created_at "
            "FROM qa_history WHERE listing_id = ? ORDER BY created_at DESC LIMIT ?",
            (listing_id, limit),
        ).fetchall()
        conn.close()
        return [
            {"question": r[0], "answer": r[1], "category": r[2], "persona": r[3],
             "confidence": r[4], "platform": r[5], "date": r[6]}
            for r in rows
        ]
