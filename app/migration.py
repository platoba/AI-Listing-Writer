"""Cross-Platform Listing Migration - migrate listings between marketplaces.

Converts listing formats, adapts content, maps categories,
handles platform-specific requirements, and validates compatibility.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


class MigrationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class Platform(str, Enum):
    AMAZON = "amazon"
    SHOPEE = "shopee"
    LAZADA = "lazada"
    ALIEXPRESS = "aliexpress"
    EBAY = "ebay"
    WALMART = "walmart"
    ETSY = "etsy"
    TEMU = "temu"
    TIKTOK_SHOP = "tiktok_shop"
    MERCADO_LIBRE = "mercado_libre"


@dataclass
class PlatformSpec:
    """Platform-specific listing requirements."""
    name: str
    title_max: int
    desc_max: int
    bullet_points: int  # 0 = not supported
    backend_keywords_max: int  # 0 = not supported
    max_images: int
    supports_html: bool
    supports_variants: bool
    required_fields: list = field(default_factory=list)
    currency: str = "USD"
    category_system: str = "flat"  # flat, tree, browse
    emoji_friendly: bool = False
    regions: list = field(default_factory=list)


@dataclass
class MigrationIssue:
    field: str
    severity: str  # error, warning, info
    message: str
    auto_fixable: bool = False
    fix_description: str = ""


@dataclass
class FieldMapping:
    source_field: str
    target_field: str
    transform: str = "copy"  # copy, truncate, convert, drop, generate
    notes: str = ""


@dataclass
class MigrationResult:
    source_platform: str
    target_platform: str
    listing_id: str
    status: MigrationStatus
    source_data: dict = field(default_factory=dict)
    migrated_data: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)
    field_mappings: list = field(default_factory=list)
    auto_fixes_applied: list = field(default_factory=list)
    compatibility_score: float = 0.0
    created_at: str = ""


@dataclass
class BatchMigrationReport:
    source_platform: str
    target_platform: str
    total: int = 0
    completed: int = 0
    failed: int = 0
    needs_review: int = 0
    avg_compatibility: float = 0.0
    common_issues: list = field(default_factory=list)
    results: list = field(default_factory=list)
    generated_at: str = ""


PLATFORM_SPECS = {
    Platform.AMAZON: PlatformSpec(
        name="Amazon", title_max=200, desc_max=2000, bullet_points=5,
        backend_keywords_max=250, max_images=9, supports_html=True,
        supports_variants=True, required_fields=["title", "price", "category", "brand"],
        category_system="browse", regions=["US", "UK", "DE", "JP", "CA", "FR", "IT", "ES", "AU"],
    ),
    Platform.SHOPEE: PlatformSpec(
        name="Shopee", title_max=120, desc_max=3000, bullet_points=0,
        backend_keywords_max=0, max_images=9, supports_html=False,
        supports_variants=True, required_fields=["title", "price", "category"],
        emoji_friendly=True, regions=["SG", "MY", "TH", "ID", "PH", "VN", "TW", "BR"],
    ),
    Platform.LAZADA: PlatformSpec(
        name="Lazada", title_max=150, desc_max=3000, bullet_points=5,
        backend_keywords_max=0, max_images=8, supports_html=True,
        supports_variants=True, required_fields=["title", "price", "category"],
        regions=["SG", "MY", "TH", "ID", "PH", "VN"],
    ),
    Platform.ALIEXPRESS: PlatformSpec(
        name="AliExpress", title_max=128, desc_max=5000, bullet_points=0,
        backend_keywords_max=0, max_images=6, supports_html=True,
        supports_variants=True, required_fields=["title", "price", "category"],
        regions=["global"],
    ),
    Platform.EBAY: PlatformSpec(
        name="eBay", title_max=80, desc_max=4000, bullet_points=0,
        backend_keywords_max=0, max_images=12, supports_html=True,
        supports_variants=True, required_fields=["title", "price", "category", "condition"],
        category_system="tree", regions=["US", "UK", "DE", "AU", "CA", "FR", "IT"],
    ),
    Platform.WALMART: PlatformSpec(
        name="Walmart", title_max=75, desc_max=4000, bullet_points=5,
        backend_keywords_max=0, max_images=10, supports_html=False,
        supports_variants=True, required_fields=["title", "price", "category", "brand", "upc"],
        regions=["US"],
    ),
    Platform.ETSY: PlatformSpec(
        name="Etsy", title_max=140, desc_max=2000, bullet_points=0,
        backend_keywords_max=13, max_images=10, supports_html=False,
        supports_variants=True, required_fields=["title", "price", "category"],
        emoji_friendly=True, regions=["global"],
    ),
    Platform.TEMU: PlatformSpec(
        name="Temu", title_max=120, desc_max=2000, bullet_points=0,
        backend_keywords_max=0, max_images=10, supports_html=False,
        supports_variants=True, required_fields=["title", "price", "category"],
        regions=["US", "EU"],
    ),
    Platform.TIKTOK_SHOP: PlatformSpec(
        name="TikTok Shop", title_max=120, desc_max=2000, bullet_points=0,
        backend_keywords_max=0, max_images=9, supports_html=False,
        supports_variants=True, required_fields=["title", "price", "category"],
        emoji_friendly=True, regions=["US", "UK", "ID", "TH", "MY", "VN", "PH", "SG"],
    ),
    Platform.MERCADO_LIBRE: PlatformSpec(
        name="Mercado Libre", title_max=60, desc_max=5000, bullet_points=0,
        backend_keywords_max=0, max_images=12, supports_html=True,
        supports_variants=True, required_fields=["title", "price", "category", "condition"],
        regions=["MX", "BR", "AR", "CO", "CL"],
    ),
}


# Common category mappings between platforms
CATEGORY_MAPPINGS = {
    ("amazon", "shopee"): {
        "Electronics": "Electronic Devices",
        "Clothing": "Women's Apparel",
        "Home & Kitchen": "Home & Living",
        "Sports & Outdoors": "Sports & Outdoors",
        "Beauty & Personal Care": "Health & Beauty",
        "Toys & Games": "Toys, Kids & Babies",
        "Books": "Stationery & Craft",
        "Pet Supplies": "Pets",
        "Automotive": "Automotive",
        "Garden & Outdoor": "Home & Living",
    },
    ("amazon", "ebay"): {
        "Electronics": "Consumer Electronics",
        "Clothing": "Clothing, Shoes & Accessories",
        "Home & Kitchen": "Home & Garden",
        "Sports & Outdoors": "Sporting Goods",
        "Beauty & Personal Care": "Health & Beauty",
        "Toys & Games": "Toys & Hobbies",
        "Books": "Books & Magazines",
        "Pet Supplies": "Pet Supplies",
        "Automotive": "eBay Motors",
    },
    ("amazon", "walmart"): {
        "Electronics": "Electronics",
        "Clothing": "Clothing",
        "Home & Kitchen": "Home",
        "Sports & Outdoors": "Sports & Outdoors",
        "Beauty & Personal Care": "Beauty",
        "Toys & Games": "Toys",
        "Books": "Books",
        "Pet Supplies": "Pets",
        "Automotive": "Auto & Tires",
    },
}


class ListingMigrator:
    """Migrate listings between e-commerce platforms."""

    def __init__(self):
        self.specs = PLATFORM_SPECS
        self.category_maps = CATEGORY_MAPPINGS

    def get_spec(self, platform: str) -> PlatformSpec:
        """Get platform specifications."""
        try:
            return self.specs[Platform(platform.lower())]
        except (ValueError, KeyError):
            raise ValueError(f"Unsupported platform: {platform}. "
                           f"Supported: {', '.join(p.value for p in Platform)}")

    def analyze_compatibility(self, listing: dict, source: str, target: str) -> tuple[float, list[MigrationIssue]]:
        """Analyze how compatible a listing is with the target platform."""
        target_spec = self.get_spec(target)
        issues = []
        score = 100.0

        # Title compatibility
        title = listing.get("title", "")
        if title and len(title) > target_spec.title_max:
            issues.append(MigrationIssue(
                field="title",
                severity="warning",
                message=f"Title too long for {target} ({len(title)}/{target_spec.title_max})",
                auto_fixable=True,
                fix_description=f"Truncate to {target_spec.title_max} chars",
            ))
            score -= 5

        # Description compatibility
        desc = listing.get("description", "")
        if desc and len(desc) > target_spec.desc_max:
            issues.append(MigrationIssue(
                field="description",
                severity="warning",
                message=f"Description too long ({len(desc)}/{target_spec.desc_max})",
                auto_fixable=True,
                fix_description=f"Truncate to {target_spec.desc_max} chars",
            ))
            score -= 5

        # HTML compatibility
        if desc and "<" in desc and not target_spec.supports_html:
            issues.append(MigrationIssue(
                field="description",
                severity="warning",
                message=f"{target} doesn't support HTML in descriptions",
                auto_fixable=True,
                fix_description="Strip HTML tags and convert to plain text",
            ))
            score -= 8

        # Bullet points
        bullets = listing.get("bullet_points", [])
        if bullets and target_spec.bullet_points == 0:
            issues.append(MigrationIssue(
                field="bullet_points",
                severity="info",
                message=f"{target} doesn't support bullet points — will merge into description",
                auto_fixable=True,
                fix_description="Append bullet points to description",
            ))
            score -= 3

        if not bullets and target_spec.bullet_points > 0:
            issues.append(MigrationIssue(
                field="bullet_points",
                severity="warning",
                message=f"{target} expects {target_spec.bullet_points} bullet points",
                auto_fixable=False,
                fix_description="Generate bullet points from description",
            ))
            score -= 10

        # Images
        images = listing.get("images", [])
        if len(images) > target_spec.max_images:
            issues.append(MigrationIssue(
                field="images",
                severity="info",
                message=f"Too many images ({len(images)}/{target_spec.max_images})",
                auto_fixable=True,
                fix_description=f"Keep first {target_spec.max_images} images",
            ))
            score -= 2

        # Backend keywords
        bk = listing.get("backend_keywords", "")
        if bk and target_spec.backend_keywords_max == 0:
            issues.append(MigrationIssue(
                field="backend_keywords",
                severity="info",
                message=f"{target} doesn't support backend keywords",
                auto_fixable=True,
                fix_description="Drop backend keywords (fold into description if possible)",
            ))
            score -= 2

        # Required fields
        for f in target_spec.required_fields:
            val = listing.get(f)
            if not val or (isinstance(val, (list, dict)) and len(val) == 0):
                issues.append(MigrationIssue(
                    field=f,
                    severity="error",
                    message=f"Missing required field for {target}: {f}",
                    auto_fixable=False,
                ))
                score -= 10

        # Category mapping
        category = listing.get("category", "")
        if category:
            mapped = self._map_category(category, source, target)
            if not mapped:
                issues.append(MigrationIssue(
                    field="category",
                    severity="warning",
                    message=f"No category mapping from {source}→{target} for '{category}'",
                    auto_fixable=False,
                    fix_description="Manual category selection required",
                ))
                score -= 8

        return max(0, min(100, score)), issues

    def migrate_listing(self, listing: dict, source: str, target: str,
                        auto_fix: bool = True) -> MigrationResult:
        """Migrate a listing from source to target platform."""
        source_spec = self.get_spec(source)
        target_spec = self.get_spec(target)
        listing_id = listing.get("id", listing.get("asin", listing.get("sku", "unknown")))
        now = datetime.utcnow().isoformat()

        compatibility, issues = self.analyze_compatibility(listing, source, target)
        migrated = dict(listing)
        mappings = []
        fixes = []

        # Title migration
        title = listing.get("title", "")
        if title:
            new_title = self._migrate_title(title, source, target, target_spec)
            if new_title != title:
                fixes.append(f"Title adapted for {target}")
            migrated["title"] = new_title
            mappings.append(FieldMapping("title", "title",
                                         "truncate" if len(title) > target_spec.title_max else "copy"))

        # Description migration
        desc = listing.get("description", "")
        if desc:
            new_desc = self._migrate_description(desc, listing, source, target, target_spec)
            if new_desc != desc:
                fixes.append(f"Description adapted for {target}")
            migrated["description"] = new_desc
            mappings.append(FieldMapping("description", "description", "convert"))

        # Bullet points
        bullets = listing.get("bullet_points", [])
        if bullets and target_spec.bullet_points == 0:
            # Merge bullets into description
            bullet_text = "\n".join(f"• {b}" for b in bullets)
            migrated["description"] = migrated.get("description", "") + "\n\n" + bullet_text
            del migrated["bullet_points"]
            fixes.append("Merged bullet points into description")
            mappings.append(FieldMapping("bullet_points", "description", "convert",
                                         "Merged into description"))
        elif not bullets and target_spec.bullet_points > 0:
            # Generate from description
            if auto_fix and desc:
                generated = self._extract_bullet_points(desc, target_spec.bullet_points)
                migrated["bullet_points"] = generated
                fixes.append(f"Generated {len(generated)} bullet points from description")
                mappings.append(FieldMapping("description", "bullet_points", "generate"))

        # Images
        images = listing.get("images", [])
        if len(images) > target_spec.max_images:
            migrated["images"] = images[:target_spec.max_images]
            fixes.append(f"Trimmed images to {target_spec.max_images}")
            mappings.append(FieldMapping("images", "images", "truncate"))

        # Keywords
        bk = listing.get("backend_keywords", "")
        if bk and target_spec.backend_keywords_max == 0:
            migrated.pop("backend_keywords", None)
            fixes.append("Removed unsupported backend keywords")
            mappings.append(FieldMapping("backend_keywords", "-", "drop"))
        elif bk and target_spec.backend_keywords_max > 0:
            if len(bk) > target_spec.backend_keywords_max:
                migrated["backend_keywords"] = bk[:target_spec.backend_keywords_max]
                fixes.append("Trimmed backend keywords")

        # Category mapping
        category = listing.get("category", "")
        if category:
            mapped = self._map_category(category, source, target)
            if mapped:
                migrated["category"] = mapped
                fixes.append(f"Category mapped: {category} → {mapped}")
                mappings.append(FieldMapping("category", "category", "convert"))

        # Determine status
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        if errors:
            status = MigrationStatus.FAILED if len(errors) > 2 else MigrationStatus.NEEDS_REVIEW
        elif warnings and not auto_fix:
            status = MigrationStatus.NEEDS_REVIEW
        else:
            status = MigrationStatus.COMPLETED

        return MigrationResult(
            source_platform=source,
            target_platform=target,
            listing_id=listing_id,
            status=status,
            source_data=listing,
            migrated_data=migrated,
            issues=[asdict(i) for i in issues],
            field_mappings=[asdict(m) for m in mappings],
            auto_fixes_applied=fixes,
            compatibility_score=compatibility,
            created_at=now,
        )

    def _migrate_title(self, title: str, source: str, target: str, spec: PlatformSpec) -> str:
        """Adapt title for target platform."""
        result = title.strip()

        # Truncate if needed
        if len(result) > spec.title_max:
            # Try to cut at word boundary
            truncated = result[:spec.title_max]
            last_space = truncated.rfind(" ")
            if last_space > spec.title_max * 0.7:
                result = truncated[:last_space]
            else:
                result = truncated

        # Add emojis for emoji-friendly platforms
        if spec.emoji_friendly and not re.search(r"[\U0001F300-\U0001F9FF]", result):
            # Don't auto-add — just note it
            pass

        return result

    def _migrate_description(self, desc: str, listing: dict, source: str,
                              target: str, spec: PlatformSpec) -> str:
        """Adapt description for target platform."""
        result = desc

        # Strip HTML if target doesn't support it
        if not spec.supports_html and "<" in result:
            result = self._strip_html(result)

        # Truncate
        if len(result) > spec.desc_max:
            result = result[:spec.desc_max]
            last_para = result.rfind("\n\n")
            if last_para > spec.desc_max * 0.7:
                result = result[:last_para]

        return result.strip()

    def _strip_html(self, html: str) -> str:
        """Convert HTML to plain text."""
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<li\s*>", "• ", text, flags=re.IGNORECASE)
        text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<p\s*>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<h[1-6][^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</h[1-6]>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_bullet_points(self, desc: str, count: int) -> list[str]:
        """Extract key points from description to create bullet points."""
        # Split into sentences
        sentences = re.split(r"[.!?]\s+", desc)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        bullets = []
        seen = set()
        for s in sentences:
            normalized = s.lower()[:30]
            if normalized not in seen and len(bullets) < count:
                # Clean up
                point = s.strip().rstrip(".")
                if len(point) > 200:
                    point = point[:200]
                bullets.append(point)
                seen.add(normalized)

        return bullets

    def _map_category(self, category: str, source: str, target: str) -> Optional[str]:
        """Map category between platforms."""
        key = (source.lower(), target.lower())
        reverse_key = (target.lower(), source.lower())

        mapping = self.category_maps.get(key, {})
        if category in mapping:
            return mapping[category]

        # Try reverse mapping
        reverse = self.category_maps.get(reverse_key, {})
        for k, v in reverse.items():
            if v == category:
                return k

        # Fuzzy match
        category_lower = category.lower()
        for k, v in mapping.items():
            if k.lower() in category_lower or category_lower in k.lower():
                return v

        return None

    def batch_migrate(self, listings: list[dict], source: str, target: str,
                      auto_fix: bool = True) -> BatchMigrationReport:
        """Migrate multiple listings."""
        results = []
        for listing in listings:
            result = self.migrate_listing(listing, source, target, auto_fix)
            results.append(result)

        completed = [r for r in results if r.status == MigrationStatus.COMPLETED]
        failed = [r for r in results if r.status == MigrationStatus.FAILED]
        review = [r for r in results if r.status == MigrationStatus.NEEDS_REVIEW]
        avg_compat = sum(r.compatibility_score for r in results) / len(results) if results else 0

        # Find common issues
        issue_counts: dict[str, int] = {}
        for r in results:
            for issue in r.issues:
                msg = issue.get("message", "")
                issue_counts[msg] = issue_counts.get(msg, 0) + 1
        common = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return BatchMigrationReport(
            source_platform=source,
            target_platform=target,
            total=len(results),
            completed=len(completed),
            failed=len(failed),
            needs_review=len(review),
            avg_compatibility=round(avg_compat, 1),
            common_issues=[{"issue": i, "count": c} for i, c in common],
            results=[asdict(r) for r in results],
            generated_at=datetime.utcnow().isoformat(),
        )

    def get_platform_comparison(self, source: str, target: str) -> dict:
        """Compare two platform specs side by side."""
        src = self.get_spec(source)
        tgt = self.get_spec(target)
        return {
            "source": {"platform": source, **asdict(src)},
            "target": {"platform": target, **asdict(tgt)},
            "differences": {
                "title_max": {"source": src.title_max, "target": tgt.title_max,
                             "action": "truncate" if src.title_max > tgt.title_max else "ok"},
                "desc_max": {"source": src.desc_max, "target": tgt.desc_max,
                            "action": "truncate" if src.desc_max > tgt.desc_max else "ok"},
                "html_support": {"source": src.supports_html, "target": tgt.supports_html,
                                "action": "strip" if src.supports_html and not tgt.supports_html else "ok"},
                "bullet_points": {"source": src.bullet_points, "target": tgt.bullet_points,
                                 "action": self._bullet_action(src, tgt)},
                "max_images": {"source": src.max_images, "target": tgt.max_images,
                              "action": "trim" if src.max_images > tgt.max_images else "ok"},
                "backend_keywords": {"source": src.backend_keywords_max, "target": tgt.backend_keywords_max},
            },
            "category_mapping_available": (source.lower(), target.lower()) in self.category_maps
                                          or (target.lower(), source.lower()) in self.category_maps,
        }

    def _bullet_action(self, src: PlatformSpec, tgt: PlatformSpec) -> str:
        if src.bullet_points > 0 and tgt.bullet_points == 0:
            return "merge_to_desc"
        elif src.bullet_points == 0 and tgt.bullet_points > 0:
            return "generate"
        return "ok"

    def format_migration_report(self, result: MigrationResult) -> str:
        """Format migration result as text."""
        status_emoji = {
            "completed": "✅", "failed": "❌",
            "needs_review": "⚠️", "pending": "⏳", "in_progress": "🔄",
        }
        lines = [
            f"{status_emoji.get(result.status.value, '📋')} Migration: {result.source_platform} → {result.target_platform}",
            f"Listing: {result.listing_id}",
            f"Compatibility: {result.compatibility_score:.0f}%",
            f"Status: {result.status.value}",
        ]

        if result.auto_fixes_applied:
            lines.append("")
            lines.append("🔧 Auto-fixes:")
            for fix in result.auto_fixes_applied:
                lines.append(f"  ✓ {fix}")

        if result.issues:
            errors = [i for i in result.issues if i.get("severity") == "error"]
            warnings = [i for i in result.issues if i.get("severity") == "warning"]
            if errors:
                lines.append("")
                lines.append("❌ Errors:")
                for e in errors:
                    lines.append(f"  • {e['message']}")
            if warnings:
                lines.append("")
                lines.append("⚠️ Warnings:")
                for w in warnings:
                    lines.append(f"  • {w['message']}")

        return "\n".join(lines)

    def format_batch_report(self, report: BatchMigrationReport) -> str:
        """Format batch migration report as text."""
        lines = [
            f"📦 Batch Migration: {report.source_platform} → {report.target_platform}",
            f"Total: {report.total} | ✅ {report.completed} | ❌ {report.failed} | ⚠️ {report.needs_review}",
            f"Avg compatibility: {report.avg_compatibility:.0f}%",
        ]

        if report.common_issues:
            lines.append("")
            lines.append("🔍 Common Issues:")
            for ci in report.common_issues[:5]:
                lines.append(f"  [{ci['count']}x] {ci['issue']}")

        return "\n".join(lines)

    @staticmethod
    def supported_platforms() -> list[str]:
        return [p.value for p in Platform]

    @staticmethod
    def supported_migrations() -> list[tuple[str, str]]:
        """List platform pairs with category mappings."""
        pairs = []
        for src in Platform:
            for tgt in Platform:
                if src != tgt:
                    pairs.append((src.value, tgt.value))
        return pairs
