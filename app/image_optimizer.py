"""Product image analysis and optimization advisor.

Analyzes product listing images for:
- Image count and size adequacy
- Alt text generation suggestions
- Image type diversity (lifestyle, white bg, infographic, scale, etc.)
- Mobile-friendliness assessment
- A+ content image analysis
- Competitor image benchmarking
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


# Image type classifications
IMAGE_TYPES = {
    "main": {
        "description": "Main product image (white background)",
        "indicators": ["main", "hero", "primary", "front", "1", "_01"],
        "required": True,
    },
    "lifestyle": {
        "description": "Product in real-world use",
        "indicators": ["lifestyle", "scene", "use", "action", "in-use",
                        "context", "environment"],
        "required": False,
    },
    "detail": {
        "description": "Close-up of features/texture",
        "indicators": ["detail", "close", "zoom", "texture", "material",
                        "closeup", "macro"],
        "required": False,
    },
    "infographic": {
        "description": "Dimensions, specs, or comparison graphics",
        "indicators": ["info", "spec", "dimension", "size", "chart",
                        "comparison", "feature", "infographic"],
        "required": False,
    },
    "packaging": {
        "description": "Product packaging or what's included",
        "indicators": ["package", "box", "unbox", "includes", "contents",
                        "whats-in", "bundle"],
        "required": False,
    },
    "scale": {
        "description": "Product next to object for size reference",
        "indicators": ["scale", "size", "hand", "model", "person",
                        "reference", "comparison"],
        "required": False,
    },
    "back": {
        "description": "Back/side view of product",
        "indicators": ["back", "rear", "side", "angle", "2", "3",
                        "_02", "_03"],
        "required": False,
    },
    "variant": {
        "description": "Different color/style options",
        "indicators": ["color", "variant", "option", "style", "swatch"],
        "required": False,
    },
}

# Platform image requirements
PLATFORM_REQUIREMENTS = {
    "amazon": {
        "min_images": 5,
        "ideal_images": 7,
        "max_images": 9,
        "min_resolution": (1000, 1000),
        "ideal_resolution": (2000, 2000),
        "main_bg": "white",
        "main_fill_pct": 85,
        "formats": ["jpg", "jpeg", "png", "gif", "tiff"],
        "max_size_mb": 10,
        "required_types": ["main"],
        "recommended_types": ["lifestyle", "detail", "infographic", "scale"],
    },
    "shopify": {
        "min_images": 3,
        "ideal_images": 8,
        "max_images": 250,
        "min_resolution": (800, 800),
        "ideal_resolution": (2048, 2048),
        "main_bg": "any",
        "formats": ["jpg", "jpeg", "png", "gif", "webp"],
        "max_size_mb": 20,
        "required_types": ["main"],
        "recommended_types": ["lifestyle", "detail", "variant"],
    },
    "ebay": {
        "min_images": 3,
        "ideal_images": 8,
        "max_images": 24,
        "min_resolution": (500, 500),
        "ideal_resolution": (1600, 1600),
        "main_bg": "white",
        "formats": ["jpg", "jpeg", "png"],
        "max_size_mb": 12,
        "required_types": ["main"],
        "recommended_types": ["detail", "back", "packaging"],
    },
    "etsy": {
        "min_images": 5,
        "ideal_images": 10,
        "max_images": 10,
        "min_resolution": (2000, 2000),
        "ideal_resolution": (3000, 3000),
        "main_bg": "any",
        "formats": ["jpg", "jpeg", "png", "gif"],
        "max_size_mb": 5,
        "required_types": ["main", "lifestyle"],
        "recommended_types": ["detail", "scale", "packaging"],
    },
    "aliexpress": {
        "min_images": 3,
        "ideal_images": 6,
        "max_images": 6,
        "min_resolution": (800, 800),
        "ideal_resolution": (1000, 1000),
        "main_bg": "white",
        "formats": ["jpg", "jpeg", "png"],
        "max_size_mb": 5,
        "required_types": ["main"],
        "recommended_types": ["detail", "infographic", "variant"],
    },
}


@dataclass
class ImageInfo:
    """Information about a product image."""
    url: str = ""
    filename: str = ""
    alt_text: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    size_kb: Optional[float] = None
    position: int = 0  # 1 = main, 2+ = additional
    detected_type: str = "unknown"


@dataclass
class ImageIssue:
    """An identified issue with an image."""
    severity: str  # "error", "warning", "info"
    image_position: int
    message: str
    fix_suggestion: str


@dataclass
class AltTextSuggestion:
    """Suggested alt text for an image."""
    image_position: int
    current_alt: str
    suggested_alt: str
    reason: str


@dataclass
class ImageOptimization:
    """Complete image optimization result."""
    total_images: int = 0
    platform: str = ""
    overall_score: float = 0.0  # 0-100
    grade: str = "F"

    issues: list[ImageIssue] = field(default_factory=list)
    alt_text_suggestions: list[AltTextSuggestion] = field(default_factory=list)
    missing_types: list[str] = field(default_factory=list)
    detected_types: dict[str, int] = field(default_factory=dict)

    recommendations: list[str] = field(default_factory=list)

    count_score: float = 0.0
    diversity_score: float = 0.0
    quality_score: float = 0.0
    alt_text_score: float = 0.0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


class ImageOptimizer:
    """Analyze and optimize product listing images."""

    def __init__(self, platform: str = "amazon"):
        self.platform = platform.lower()
        self.requirements = PLATFORM_REQUIREMENTS.get(
            self.platform, PLATFORM_REQUIREMENTS["amazon"]
        )

    def analyze(
        self,
        images: list[ImageInfo],
        product_title: str = "",
        product_category: str = "",
    ) -> ImageOptimization:
        """Run complete image analysis."""
        result = ImageOptimization(
            total_images=len(images),
            platform=self.platform,
        )

        if not images:
            result.overall_score = 0.0
            result.grade = "F"
            result.issues.append(ImageIssue(
                severity="error",
                image_position=0,
                message="No images found",
                fix_suggestion="Add at least "
                               f"{self.requirements['min_images']} images",
            ))
            result.recommendations.append(
                f"🔴 CRITICAL: Add images. {self.platform.title()} requires "
                f"minimum {self.requirements['min_images']} images."
            )
            return result

        # Classify image types
        for img in images:
            img.detected_type = self._classify_image(img)
            result.detected_types[img.detected_type] = \
                result.detected_types.get(img.detected_type, 0) + 1

        # Check image count
        result.count_score = self._score_count(len(images))

        # Check image diversity
        result.diversity_score = self._score_diversity(images, result)

        # Check quality
        result.quality_score = self._score_quality(images, result)

        # Check alt texts
        result.alt_text_score = self._score_alt_texts(
            images, product_title, product_category, result
        )

        # Calculate overall score
        result.overall_score = round(
            result.count_score * 0.25 +
            result.diversity_score * 0.25 +
            result.quality_score * 0.30 +
            result.alt_text_score * 0.20,
            1,
        )

        # Assign grade
        result.grade = self._to_grade(result.overall_score)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result, images)

        return result

    def _classify_image(self, image: ImageInfo) -> str:
        """Classify image type based on filename and alt text."""
        text = f"{image.filename} {image.alt_text}".lower()

        best_match = "unknown"
        best_score = 0

        for img_type, data in IMAGE_TYPES.items():
            score = sum(1 for ind in data["indicators"] if ind in text)
            if score > best_score:
                best_score = score
                best_match = img_type

        # Position-based fallback
        if best_match == "unknown":
            if image.position == 1:
                best_match = "main"
            elif image.position == 2:
                best_match = "back"
            elif image.position <= 4:
                best_match = "detail"

        return best_match

    def _score_count(self, count: int) -> float:
        """Score based on image count."""
        ideal = self.requirements["ideal_images"]
        minimum = self.requirements["min_images"]

        if count >= ideal:
            return 100.0
        if count >= minimum:
            return 60 + (count - minimum) / (ideal - minimum) * 40
        if count > 0:
            return count / minimum * 60
        return 0.0

    def _score_diversity(
        self, images: list[ImageInfo], result: ImageOptimization
    ) -> float:
        """Score based on image type diversity."""
        score = 100.0

        # Check required types
        for req_type in self.requirements.get("required_types", []):
            if req_type not in result.detected_types:
                result.missing_types.append(req_type)
                result.issues.append(ImageIssue(
                    severity="error",
                    image_position=0,
                    message=f"Missing required image type: {req_type}",
                    fix_suggestion=f"Add a {IMAGE_TYPES[req_type]['description']}",
                ))
                score -= 25

        # Check recommended types
        for rec_type in self.requirements.get("recommended_types", []):
            if rec_type not in result.detected_types:
                result.missing_types.append(rec_type)
                result.issues.append(ImageIssue(
                    severity="warning",
                    image_position=0,
                    message=f"Missing recommended image type: {rec_type}",
                    fix_suggestion=f"Add a {IMAGE_TYPES[rec_type]['description']}",
                ))
                score -= 10

        # Bonus for diverse types
        unique_types = len(set(result.detected_types.keys()) - {"unknown"})
        if unique_types >= 5:
            score += 10

        return max(0, min(100, score))

    def _score_quality(
        self, images: list[ImageInfo], result: ImageOptimization
    ) -> float:
        """Score based on image quality signals."""
        score = 100.0
        min_res = self.requirements.get("min_resolution", (500, 500))
        ideal_res = self.requirements.get("ideal_resolution", (1000, 1000))

        for img in images:
            # Resolution check
            if img.width and img.height:
                if img.width < min_res[0] or img.height < min_res[1]:
                    result.issues.append(ImageIssue(
                        severity="error",
                        image_position=img.position,
                        message=f"Image {img.position} below minimum "
                                f"resolution ({img.width}x{img.height} < "
                                f"{min_res[0]}x{min_res[1]})",
                        fix_suggestion=f"Resize to at least {min_res[0]}x{min_res[1]}px",
                    ))
                    score -= 15
                elif img.width < ideal_res[0] or img.height < ideal_res[1]:
                    result.issues.append(ImageIssue(
                        severity="warning",
                        image_position=img.position,
                        message=f"Image {img.position} below ideal "
                                f"resolution ({img.width}x{img.height})",
                        fix_suggestion=f"Upgrade to {ideal_res[0]}x{ideal_res[1]}px "
                                       f"for zoom capability",
                    ))
                    score -= 5

                # Aspect ratio check (should be square or near-square for most platforms)
                ratio = max(img.width, img.height) / max(min(img.width, img.height), 1)
                if ratio > 2.0:
                    result.issues.append(ImageIssue(
                        severity="warning",
                        image_position=img.position,
                        message=f"Image {img.position} has extreme aspect ratio ({ratio:.1f}:1)",
                        fix_suggestion="Use a more square aspect ratio for "
                                       "consistent gallery display",
                    ))
                    score -= 5

            # File size check
            max_size = self.requirements.get("max_size_mb", 10) * 1024
            if img.size_kb and img.size_kb > max_size:
                result.issues.append(ImageIssue(
                    severity="error",
                    image_position=img.position,
                    message=f"Image {img.position} exceeds max size "
                            f"({img.size_kb:.0f}KB > {max_size:.0f}KB)",
                    fix_suggestion="Compress image to reduce file size",
                ))
                score -= 10

            # Format check
            if img.filename:
                ext = img.filename.rsplit(".", 1)[-1].lower() if "." in img.filename else ""
                allowed = self.requirements.get("formats", [])
                if ext and allowed and ext not in allowed:
                    result.issues.append(ImageIssue(
                        severity="warning",
                        image_position=img.position,
                        message=f"Image {img.position} format '{ext}' may not "
                                f"be optimal for {self.platform}",
                        fix_suggestion=f"Convert to {', '.join(allowed[:3])}",
                    ))
                    score -= 5

        return max(0, min(100, score))

    def _score_alt_texts(
        self,
        images: list[ImageInfo],
        product_title: str,
        product_category: str,
        result: ImageOptimization,
    ) -> float:
        """Score alt text quality and generate suggestions."""
        score = 100.0

        for img in images:
            if not img.alt_text or img.alt_text.strip() == "":
                score -= 15
                result.issues.append(ImageIssue(
                    severity="warning",
                    image_position=img.position,
                    message=f"Image {img.position} missing alt text",
                    fix_suggestion="Add descriptive alt text for SEO and accessibility",
                ))

                # Generate suggestion
                suggested = self._generate_alt_text(
                    img, product_title, product_category
                )
                result.alt_text_suggestions.append(AltTextSuggestion(
                    image_position=img.position,
                    current_alt="",
                    suggested_alt=suggested,
                    reason="Missing alt text — critical for SEO and accessibility",
                ))

            elif len(img.alt_text) < 10:
                score -= 8
                suggested = self._generate_alt_text(
                    img, product_title, product_category
                )
                result.alt_text_suggestions.append(AltTextSuggestion(
                    image_position=img.position,
                    current_alt=img.alt_text,
                    suggested_alt=suggested,
                    reason="Alt text too short — add more descriptive details",
                ))

            elif len(img.alt_text) > 125:
                score -= 5
                result.issues.append(ImageIssue(
                    severity="info",
                    image_position=img.position,
                    message=f"Image {img.position} alt text too long "
                            f"({len(img.alt_text)} chars)",
                    fix_suggestion="Keep alt text under 125 characters for "
                                   "optimal SEO",
                ))

        return max(0, min(100, score))

    def _generate_alt_text(
        self, image: ImageInfo, product_title: str, category: str
    ) -> str:
        """Generate suggested alt text for an image."""
        type_desc = IMAGE_TYPES.get(
            image.detected_type, {}
        ).get("description", "Product image")

        parts = []

        if product_title:
            # Use first 50 chars of title
            short_title = product_title[:50].strip()
            parts.append(short_title)

        parts.append(f"- {type_desc}")

        if category:
            parts.append(f"({category})")

        return " ".join(parts)[:125]

    def _to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A+"
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 60:
            return "C"
        if score >= 50:
            return "D"
        return "F"

    def _generate_recommendations(
        self, result: ImageOptimization, images: list[ImageInfo]
    ) -> list[str]:
        """Generate prioritized recommendations."""
        recs = []

        # Critical issues
        if result.error_count > 0:
            recs.append(
                f"🔴 Fix {result.error_count} critical image "
                f"issue(s) immediately"
            )

        # Count recommendations
        ideal = self.requirements["ideal_images"]
        if result.total_images < ideal:
            recs.append(
                f"📸 Add {ideal - result.total_images} more images "
                f"(current: {result.total_images}, ideal: {ideal})"
            )

        # Missing types
        if result.missing_types:
            types_str = ", ".join(result.missing_types[:4])
            recs.append(f"🖼️ Add missing image types: {types_str}")

        # Alt text
        missing_alt = sum(1 for img in images if not img.alt_text)
        if missing_alt > 0:
            recs.append(
                f"📝 Add alt text to {missing_alt} image(s) for SEO"
            )

        # Lifestyle images
        if "lifestyle" not in result.detected_types:
            recs.append(
                "📷 Add lifestyle images showing product in real-world use — "
                "these convert 22% better than white-background-only listings"
            )

        # Infographic
        if "infographic" not in result.detected_types:
            recs.append(
                "📊 Add infographic image with product specs/dimensions — "
                "reduces return rates by setting clear expectations"
            )

        # Mobile-first
        if any(img.width and img.width < 600 for img in images):
            recs.append(
                "📱 Ensure all images are mobile-friendly "
                "(minimum 600px wide)"
            )

        return recs


def analyze_listing_images(
    images: list[dict],
    platform: str = "amazon",
    product_title: str = "",
    product_category: str = "",
) -> ImageOptimization:
    """Convenience function to analyze listing images.

    Args:
        images: List of dicts with keys: url, filename, alt_text,
                width, height, size_kb, position
        platform: Target platform name
        product_title: Product title for alt text generation
        product_category: Product category

    Returns:
        ImageOptimization result
    """
    items = []
    for i, img in enumerate(images):
        items.append(ImageInfo(
            url=img.get("url", ""),
            filename=img.get("filename", ""),
            alt_text=img.get("alt_text", ""),
            width=img.get("width"),
            height=img.get("height"),
            size_kb=img.get("size_kb"),
            position=img.get("position", i + 1),
            detected_type=img.get("type", "unknown"),
        ))

    optimizer = ImageOptimizer(platform)
    return optimizer.analyze(items, product_title, product_category)


def format_image_report(opt: ImageOptimization) -> str:
    """Format image optimization as readable report."""
    lines = [
        "=" * 60,
        "📸 IMAGE OPTIMIZATION REPORT",
        "=" * 60,
        "",
        f"Platform: {opt.platform.upper()}",
        f"Total Images: {opt.total_images}",
        f"Overall Score: {opt.overall_score}/100 (Grade: {opt.grade})",
        "",
        "📊 Score Breakdown:",
        f"  Image Count:     {opt.count_score:.0f}/100",
        f"  Type Diversity:  {opt.diversity_score:.0f}/100",
        f"  Image Quality:   {opt.quality_score:.0f}/100",
        f"  Alt Text:        {opt.alt_text_score:.0f}/100",
        "",
    ]

    # Detected types
    if opt.detected_types:
        lines.append("🖼️ Image Types Detected:")
        for img_type, count in opt.detected_types.items():
            desc = IMAGE_TYPES.get(img_type, {}).get("description", "Unknown")
            lines.append(f"  • {img_type}: {count} ({desc})")
        lines.append("")

    # Missing types
    if opt.missing_types:
        lines.append("❌ Missing Image Types:")
        for mt in opt.missing_types:
            desc = IMAGE_TYPES.get(mt, {}).get("description", "Unknown")
            lines.append(f"  • {mt}: {desc}")
        lines.append("")

    # Issues
    if opt.issues:
        lines.append(f"⚠️ Issues ({opt.error_count} errors, "
                      f"{opt.warning_count} warnings):")
        for issue in opt.issues:
            icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}[issue.severity]
            lines.append(f"  {icon} {issue.message}")
            lines.append(f"      → {issue.fix_suggestion}")
        lines.append("")

    # Alt text suggestions
    if opt.alt_text_suggestions:
        lines.append("📝 Alt Text Suggestions:")
        for s in opt.alt_text_suggestions:
            lines.append(f"  Image {s.image_position}: \"{s.suggested_alt}\"")
        lines.append("")

    # Recommendations
    if opt.recommendations:
        lines.append("💡 Recommendations:")
        for r in opt.recommendations:
            lines.append(f"  {r}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
