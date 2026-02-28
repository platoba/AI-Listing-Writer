"""Bulk listing processor.

Process multiple products from CSV/JSON input, generating listings
for one or more platforms in batch mode.
"""
import csv
import io
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

from app.platforms import PLATFORMS


class BulkStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BulkItem:
    product: str
    platforms: list[str]
    language: str = "English"
    extra_instructions: str = ""
    status: BulkStatus = BulkStatus.PENDING
    results: dict[str, str] = field(default_factory=dict)  # platform -> listing
    errors: dict[str, str] = field(default_factory=dict)   # platform -> error msg
    duration_ms: int = 0


@dataclass
class BulkResult:
    items: list[BulkItem] = field(default_factory=list)
    total_generated: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    elapsed_ms: int = 0

    def summary(self) -> str:
        total = len(self.items)
        lines = [
            f"📦 Bulk Processing Complete",
            f"   Total products: {total}",
            f"   ✅ Generated: {self.total_generated}",
            f"   ❌ Failed: {self.total_failed}",
            f"   ⏭️  Skipped: {self.total_skipped}",
            f"   ⏱️  Time: {self.elapsed_ms / 1000:.1f}s",
        ]
        return "\n".join(lines)


def parse_csv(csv_text: str) -> list[dict]:
    """Parse CSV text into product records.

    Expected columns: product, platform(s), language, instructions
    Only 'product' is required.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    records = []
    for row in reader:
        # Normalize column names (case-insensitive)
        normalized = {k.strip().lower(): v.strip() for k, v in row.items() if v}
        product = (
            normalized.get("product")
            or normalized.get("产品")
            or normalized.get("name")
            or normalized.get("商品")
            or ""
        )
        if not product:
            continue

        platforms_str = (
            normalized.get("platform")
            or normalized.get("platforms")
            or normalized.get("平台")
            or "amazon"
        )
        platforms = [p.strip().lower() for p in platforms_str.split(",")]

        language = (
            normalized.get("language")
            or normalized.get("lang")
            or normalized.get("语言")
            or "English"
        )

        instructions = (
            normalized.get("instructions")
            or normalized.get("extra")
            or normalized.get("备注")
            or ""
        )

        records.append({
            "product": product,
            "platforms": platforms,
            "language": language,
            "instructions": instructions,
        })
    return records


def parse_json(json_text: str) -> list[dict]:
    """Parse JSON text into product records.

    Accepts array of objects or {"products": [...]}
    """
    data = json.loads(json_text)
    if isinstance(data, dict):
        data = data.get("products", data.get("items", []))
    if not isinstance(data, list):
        raise ValueError("JSON must be an array or contain a 'products' array")

    records = []
    for item in data:
        if isinstance(item, str):
            # Simple string = product name, default platform
            records.append({
                "product": item,
                "platforms": ["amazon"],
                "language": "English",
                "instructions": "",
            })
        elif isinstance(item, dict):
            product = item.get("product") or item.get("name") or item.get("产品", "")
            if not product:
                continue
            platforms = item.get("platforms") or item.get("platform", "amazon")
            if isinstance(platforms, str):
                platforms = [p.strip().lower() for p in platforms.split(",")]
            records.append({
                "product": product,
                "platforms": platforms,
                "language": item.get("language", item.get("lang", "English")),
                "instructions": item.get("instructions", item.get("extra", "")),
            })
    return records


def parse_input(text: str) -> list[dict]:
    """Auto-detect format (CSV or JSON) and parse."""
    stripped = text.strip()
    if stripped.startswith("[") or stripped.startswith("{"):
        return parse_json(stripped)
    return parse_csv(stripped)


def process_bulk(
    records: list[dict],
    generate_fn: Callable[[str, str, str], str],
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    max_items: int = 50,
) -> BulkResult:
    """Process a batch of product records.

    Args:
        records: List of parsed product dicts.
        generate_fn: Function(product, platform, language) -> listing text.
        on_progress: Optional callback(current, total, product_name).
        max_items: Safety limit on batch size.

    Returns:
        BulkResult with all items and stats.
    """
    result = BulkResult()
    start = time.time()

    # Apply limit
    if len(records) > max_items:
        records = records[:max_items]

    for i, rec in enumerate(records):
        item = BulkItem(
            product=rec["product"],
            platforms=rec["platforms"],
            language=rec.get("language", "English"),
            extra_instructions=rec.get("instructions", ""),
        )

        if on_progress:
            on_progress(i + 1, len(records), item.product)

        item.status = BulkStatus.PROCESSING
        item_start = time.time()

        for platform in item.platforms:
            if platform not in PLATFORMS:
                item.errors[platform] = f"Unknown platform: {platform}"
                result.total_failed += 1
                continue

            try:
                prompt_extra = ""
                if item.extra_instructions:
                    prompt_extra = f"\nAdditional instructions: {item.extra_instructions}"

                listing = generate_fn(
                    item.product + prompt_extra,
                    platform,
                    item.language,
                )
                item.results[platform] = listing
                result.total_generated += 1
            except Exception as e:
                item.errors[platform] = str(e)
                result.total_failed += 1

        item.duration_ms = int((time.time() - item_start) * 1000)
        item.status = (
            BulkStatus.DONE
            if item.results
            else BulkStatus.FAILED
            if item.errors
            else BulkStatus.SKIPPED
        )
        if item.status == BulkStatus.SKIPPED:
            result.total_skipped += 1

        result.items.append(item)

    result.elapsed_ms = int((time.time() - start) * 1000)
    return result


def bulk_to_csv(result: BulkResult) -> str:
    """Export bulk results to CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Product", "Platform", "Status", "Listing Preview", "Error"])
    for item in result.items:
        for platform in item.platforms:
            listing = item.results.get(platform, "")
            error = item.errors.get(platform, "")
            status = "✅" if listing else "❌" if error else "⏭️"
            writer.writerow([
                item.product,
                platform,
                status,
                listing[:300] if listing else "",
                error,
            ])
    return buf.getvalue()


def bulk_to_json(result: BulkResult) -> str:
    """Export bulk results to JSON."""
    data = {
        "summary": {
            "total_products": len(result.items),
            "generated": result.total_generated,
            "failed": result.total_failed,
            "skipped": result.total_skipped,
            "elapsed_ms": result.elapsed_ms,
        },
        "items": [],
    }
    for item in result.items:
        data["items"].append({
            "product": item.product,
            "platforms": item.platforms,
            "language": item.language,
            "status": item.status.value,
            "results": item.results,
            "errors": item.errors,
            "duration_ms": item.duration_ms,
        })
    return json.dumps(data, ensure_ascii=False, indent=2)
