"""CLI tool for AI Listing Writer.

Usage:
    python -m app.cli generate --product "..." --platform amazon [--lang English]
    python -m app.cli validate --file listing.txt --platform amazon
    python -m app.cli score --file listing.txt [--platform amazon] [--keywords "kw1,kw2"]
    python -m app.cli bulk --file products.csv
    python -m app.cli ab --product "..." --platform amazon [--variants 3]
    python -m app.cli translate --file listing.txt --target ja-JP [--source en-US]
    python -m app.cli stats [--user 123] [--days 30]
    python -m app.cli locales
    python -m app.cli platforms
"""
import argparse
import sys
import json


def cmd_generate(args):
    """Generate a listing for a product."""
    from app.platforms import PLATFORMS
    from app.ai_engine import call_ai

    platform = args.platform.lower()
    if platform not in PLATFORMS:
        print(f"❌ Unknown platform: {platform}")
        print(f"Available: {', '.join(PLATFORMS.keys())}")
        sys.exit(1)

    tmpl = PLATFORMS[platform]["template"]
    prompt = tmpl.format(product=args.product, lang=args.lang)

    print(f"🔄 Generating {platform} listing for: {args.product}")
    result = call_ai(prompt)
    print(result)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"\n💾 Saved to {args.output}")


def cmd_validate(args):
    """Validate a listing against platform rules."""
    from app.validator import validate_listing

    text = _read_input(args.file, args.text)
    if not text:
        print("❌ No input. Use --file or --text")
        sys.exit(1)

    result = validate_listing(text, args.platform)
    print(result.summary())
    print()
    for issue in result.issues:
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[issue.severity.value]
        print(f"  {icon} [{issue.field}] {issue.message}")
        if issue.suggestion:
            print(f"     💡 {issue.suggestion}")


def cmd_score(args):
    """Score a listing's SEO quality."""
    from app.scoring import score_listing

    text = _read_input(args.file, args.text)
    if not text:
        print("❌ No input. Use --file or --text")
        sys.exit(1)

    keywords = args.keywords.split(",") if args.keywords else None
    result = score_listing(text, args.platform, keywords)
    print(result.summary())


def cmd_bulk(args):
    """Process a bulk file of products."""
    from app.bulk import parse_input, process_bulk, bulk_to_csv, bulk_to_json
    from app.platforms import PLATFORMS
    from app.ai_engine import call_ai

    with open(args.file) as f:
        content = f.read()

    records = parse_input(content)
    print(f"📦 Parsed {len(records)} products")

    def generate_fn(product, platform, language):
        tmpl = PLATFORMS[platform]["template"]
        prompt = tmpl.format(product=product, lang=language)
        return call_ai(prompt)

    def on_progress(current, total, name):
        print(f"  [{current}/{total}] {name}")

    result = process_bulk(records, generate_fn, on_progress, max_items=args.max)
    print()
    print(result.summary())

    if args.output:
        fmt = args.output.rsplit(".", 1)[-1] if "." in args.output else "csv"
        data = bulk_to_json(result) if fmt == "json" else bulk_to_csv(result)
        with open(args.output, "w") as f:
            f.write(data)
        print(f"💾 Saved to {args.output}")


def cmd_ab(args):
    """Generate A/B test variants."""
    from app.ab_testing import generate_ab_plan

    angles = args.angles.split(",") if args.angles else None
    plan = generate_ab_plan(
        args.product, args.platform,
        angles=angles,
        num_variants=args.variants,
        language=args.lang,
    )
    print(plan.summary())


def cmd_translate(args):
    """Translate a listing to another locale."""
    from app.translator import translate_listing

    text = _read_input(args.file, args.text)
    if not text:
        print("❌ No input. Use --file or --text")
        sys.exit(1)

    result = translate_listing(text, args.target, args.source, args.platform)
    print(result.summary())
    print()
    print(result.translated)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result.translated)
        print(f"\n💾 Saved to {args.output}")


def cmd_stats(args):
    """Show analytics stats."""
    from app.analytics import get_user_stats, get_global_stats, init_db

    init_db()
    if args.user:
        stats = get_user_stats(args.user)
        print(stats.summary())
    else:
        stats = get_global_stats()
        print("📊 Global Statistics")
        print(f"   Total listings: {stats['total_generations']}")
        print(f"   Today: {stats['today']}")
        if stats["platforms"]:
            print("   Platforms:")
            for p, info in stats["platforms"].items():
                print(f"     {p}: {info['count']} (avg score: {info['avg_score']})")


def cmd_locales(args):
    """List available locales."""
    from app.translator import list_locales
    print(list_locales())


def cmd_platforms(args):
    """List available platforms."""
    from app.platforms import list_platforms
    print("📋 Available Platforms:")
    print(list_platforms())


def _read_input(file_path=None, text=None):
    """Read input from file or text argument."""
    if file_path:
        with open(file_path) as f:
            return f.read()
    if text:
        return text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def main():
    parser = argparse.ArgumentParser(
        prog="ai-listing-writer",
        description="AI Listing Writer CLI — Generate, validate, score, and translate product listings",
    )
    sub = parser.add_subparsers(dest="command", help="Command")

    # generate
    p = sub.add_parser("generate", help="Generate a listing")
    p.add_argument("--product", "-p", required=True, help="Product name/description")
    p.add_argument("--platform", default="amazon", help="Target platform")
    p.add_argument("--lang", default="English", help="Output language")
    p.add_argument("--output", "-o", help="Save output to file")

    # validate
    p = sub.add_parser("validate", help="Validate a listing")
    p.add_argument("--file", "-f", help="Input file")
    p.add_argument("--text", "-t", help="Input text")
    p.add_argument("--platform", default="amazon", help="Platform rules")

    # score
    p = sub.add_parser("score", help="Score listing SEO quality")
    p.add_argument("--file", "-f", help="Input file")
    p.add_argument("--text", "-t", help="Input text")
    p.add_argument("--platform", default="amazon", help="Platform")
    p.add_argument("--keywords", "-k", help="Target keywords (comma-separated)")

    # bulk
    p = sub.add_parser("bulk", help="Bulk process from CSV/JSON")
    p.add_argument("--file", "-f", required=True, help="Input CSV/JSON file")
    p.add_argument("--output", "-o", help="Output file")
    p.add_argument("--max", type=int, default=50, help="Max items to process")

    # ab
    p = sub.add_parser("ab", help="Generate A/B test variants")
    p.add_argument("--product", "-p", required=True, help="Product name")
    p.add_argument("--platform", default="amazon", help="Platform")
    p.add_argument("--variants", "-n", type=int, default=3, help="Number of variants")
    p.add_argument("--angles", help="Specific angles (comma-separated)")
    p.add_argument("--lang", default="English", help="Language")

    # translate
    p = sub.add_parser("translate", help="Translate and localize a listing")
    p.add_argument("--file", "-f", help="Input file")
    p.add_argument("--text", "-t", help="Input text")
    p.add_argument("--target", required=True, help="Target locale (e.g. ja-JP)")
    p.add_argument("--source", default="en-US", help="Source locale")
    p.add_argument("--platform", default="amazon", help="Platform")
    p.add_argument("--output", "-o", help="Save output to file")

    # stats
    p = sub.add_parser("stats", help="Show analytics")
    p.add_argument("--user", type=int, help="User ID filter")
    p.add_argument("--days", type=int, default=30, help="Days of data")

    # locales
    sub.add_parser("locales", help="List available locales")

    # platforms
    sub.add_parser("platforms", help="List available platforms")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "generate": cmd_generate,
        "validate": cmd_validate,
        "score": cmd_score,
        "bulk": cmd_bulk,
        "ab": cmd_ab,
        "translate": cmd_translate,
        "stats": cmd_stats,
        "locales": cmd_locales,
        "platforms": cmd_platforms,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
