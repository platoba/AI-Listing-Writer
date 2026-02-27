"""Export listings to multiple formats (CSV, JSON, TXT, HTML)."""
import csv
import io
import json
import time
from typing import Optional


def export_csv(records: list[dict]) -> str:
    """Export listing records to CSV string."""
    if not records:
        return ""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Platform", "Product", "Generated At", "Preview"])
    for r in records:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("ts", 0)))
        writer.writerow([
            r.get("platform", ""),
            r.get("product", ""),
            ts,
            r.get("preview", "")[:200],
        ])
    return buf.getvalue()


def export_json(records: list[dict], pretty: bool = True) -> str:
    """Export listing records to JSON string."""
    clean = []
    for r in records:
        clean.append({
            "platform": r.get("platform", ""),
            "product": r.get("product", ""),
            "generated_at": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(r.get("ts", 0))
            ),
            "preview": r.get("preview", ""),
        })
    return json.dumps(clean, ensure_ascii=False, indent=2 if pretty else None)


def export_txt(records: list[dict]) -> str:
    """Export listing records to plain text."""
    if not records:
        return "No records."
    lines = ["AI Listing Writer - Export", "=" * 40, ""]
    for i, r in enumerate(records, 1):
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("ts", 0)))
        lines.append(f"#{i} [{r.get('platform', '?')}] {r.get('product', '?')}")
        lines.append(f"   Time: {ts}")
        lines.append(f"   {r.get('preview', '')[:300]}")
        lines.append("")
    return "\n".join(lines)


def export_html(records: list[dict]) -> str:
    """Export listing records to a simple HTML table."""
    if not records:
        return "<p>No records.</p>"
    rows = []
    for r in records:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("ts", 0)))
        rows.append(
            f"<tr><td>{_esc(r.get('platform',''))}</td>"
            f"<td>{_esc(r.get('product',''))}</td>"
            f"<td>{ts}</td>"
            f"<td>{_esc(r.get('preview','')[:200])}</td></tr>"
        )
    return (
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<tr><th>Platform</th><th>Product</th><th>Time</th><th>Preview</th></tr>"
        + "".join(rows)
        + "</table>"
    )


EXPORTERS = {
    "csv": export_csv,
    "json": export_json,
    "txt": export_txt,
    "html": export_html,
}


def export_records(records: list[dict], fmt: str = "csv") -> Optional[str]:
    """Export records in the given format. Returns None if format unknown."""
    fn = EXPORTERS.get(fmt.lower())
    if fn is None:
        return None
    return fn(records)


def _esc(s: str) -> str:
    """Minimal HTML escape."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
