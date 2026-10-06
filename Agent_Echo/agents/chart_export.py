"""Draw approved SQL rows as local SVG files; no model-generated code or website."""

import csv
from datetime import date
from html import escape
import json
import math
from pathlib import Path
import textwrap

COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#A6761D", "#555555")


def svg_chart(chart, rows, scope):
    width, height, left, right, top, bottom = 1120, 720, 110, 40, 90, 210
    plot_w, plot_h = width - left - right, height - top - bottom
    categories = sorted({str(row[chart["x"]]) for row in rows}) if chart["kind"] == "line" else list(dict.fromkeys(str(row[chart["x"]]) for row in rows))
    groups = list(dict.fromkeys(str(row[chart["series"]]) if chart["series"] else "All" for row in rows))
    values = [row[chart["y"]] for row in rows if row[chart["y"]] is not None]
    low, high = min(0, min(values)), max(0, max(values))
    if low == high:
        high = low + 1
    span = high - low
    high += span * .12
    if low < 0:
        low -= span * .06
    raw_step = (high - low) / 5
    magnitude = 10 ** math.floor(math.log10(raw_step))
    step = next(number * magnitude for number in (1, 2, 5, 10) if number * magnitude >= raw_step)
    low, high = math.floor(low / step) * step, math.ceil(high / step) * step
    y_pos = lambda value: top + plot_h * (high - value) / (high - low)
    band = plot_w / len(categories)
    x_pos = lambda index: left + band * (index + .5)
    if chart["kind"] == "line":
        times = [date(int(value[:4]), (int(value[-1]) - 1) * 3 + 1, 1).toordinal()
                 if "-Q" in value else date.fromisoformat(value).toordinal() for value in categories]
        interval = times[-1] - times[0]
        x_pos = lambda index: left + band/2 + ((times[index] - times[0]) / interval * (plot_w - band) if interval else 0)
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f'<title>{escape(chart["title"])}</title>',
        f'<desc>{escape(chart["kind"])} chart of {escape(chart["y"])} by {escape(chart["x"])}. '
        f'Source {escape(chart["source_id"])}; synthetic data; missing values are not zero.</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g font-family="Arial, sans-serif" fill="#222222">']
    def text(x, y, value, size=15, anchor="start", extra=""):
        elements.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" {extra}>{escape(str(value))}</text>')
    text(left, 34, chart["title"], 22)
    text(left, 61, f'{chart["y_label"]} · {chart["unit"]}', 16)
    for tick in range(round((high - low) / step) + 1):
        value = low + step * tick
        py = y_pos(value)
        elements.append(f'<line x1="{left}" x2="{width-right}" y1="{py:.2f}" y2="{py:.2f}" stroke="#dddddd"/>')
        text(left - 12, py + 5, f"{value:.2f}".rstrip("0").rstrip("."), anchor="end")
    baseline = y_pos(0)
    elements.append(f'<line x1="{left}" x2="{width-right}" y1="{baseline:.2f}" y2="{baseline:.2f}" stroke="#555555"/>')
    for index, category in enumerate(categories):
        px = x_pos(index)
        if chart["kind"] == "line":
            text(px, top + plot_h + 25, category, 13, "end", f'transform="rotate(-35 {px:.2f} {top+plot_h+25})"')
        else:
            lines = textwrap.wrap(category, width=max(8, min(24, int(band / 8))))[:4]
            for offset, label in enumerate(lines):
                text(px, top + plot_h + 24 + offset * 17, label, 13, "middle")
    lookup = {(str(row[chart["x"]]), str(row[chart["series"]]) if chart["series"] else "All"): row for row in rows}
    for group_index, group in enumerate(groups):
        color, points = COLORS[group_index], []
        for category_index, category in enumerate(categories):
            row = lookup.get((category, group))
            value = row[chart["y"]] if row else None
            px = x_pos(category_index)
            if value is None:
                if points:
                    elements.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
                    points = []
                missing_x = px if chart["kind"] == "line" else px - band*.36 + (group_index+.5)*band*.72/len(groups)
                text(missing_x, top + plot_h - 6, "N/A", 12, "middle")
                continue
            py = y_pos(value)
            denominator = f'; {chart["denominator"]}={row[chart["denominator"]]}' if chart["denominator"] else ""
            tooltip = escape(f'{category}; {group}; {chart["y"]}={value}{denominator}; [{chart["source_id"]}]')
            if chart["kind"] == "bar":
                bar_w = band * .72 / len(groups)
                bx = px - band * .36 + group_index * bar_w
                elements.append(f'<rect x="{bx:.2f}" y="{min(py,baseline):.2f}" width="{max(1,bar_w-2):.2f}" height="{abs(baseline-py):.2f}" fill="{color}"><title>{tooltip}</title></rect>')
                text(bx + bar_w/2, py - 7 if value >= 0 else py + 17, f"{value:g}", 12, "middle")
            else:
                points.append(f"{px:.2f},{py:.2f}")
                elements.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" fill="{color}"><title>{tooltip}</title></circle>')
        if chart["kind"] == "line" and points:
            elements.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
        if chart["series"]:
            lx, ly = left + (group_index % 3) * 310, height - 102 + (group_index // 3) * 23
            elements.append(f'<rect x="{lx}" y="{ly-12}" width="12" height="12" fill="{color}"/>')
            text(lx + 21, ly, group[:38], 13)
    text(left + plot_w/2, height - 132, chart["x_label"], 16, "middle")
    text(left, height - 38, f'Synthetic data · Source [{chart["source_id"]}] · Manager {scope.manager_id} · {scope.start_date} to {scope.end_date}', 13)
    text(left, height - 16, f'Denominator: {chart["denominator"] or "not a rate"} · Exact rows and missing values are preserved in the companion CSV.', 12)
    elements.append('</g></svg>')
    return "\n".join(elements)


def export_charts(charts, evidence, scope, output_dir):
    if not charts:
        return []
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = {item["citation_id"]: item for item in evidence}
    files = []
    for number, chart in enumerate(charts, 1):
        source = sources[chart["source_id"]]
        rows = source["rows"]
        stem = output_dir / f"chart_{number:02d}"
        svg_path, csv_path, meta_path = stem.with_suffix(".svg"), stem.with_suffix(".csv"), stem.with_suffix(".json")
        svg_path.write_text(svg_chart(chart, rows, scope), encoding="utf-8")
        columns = list(dict.fromkeys(chart[key] for key in ("x", "y", "series", "denominator") if chart[key] is not None))
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, columns)
            writer.writeheader()
            writer.writerows({key: row[key] for key in columns} for row in rows)
        meta_path.write_text(json.dumps({"chart": chart, "scope": scope.__dict__, "synthetic": True,
            "source_agent": source["producer"], "source_sql": source["sql"], "row_count": len(rows), "truncated": False}, indent=2), encoding="utf-8")
        files.append({"source_id": chart["source_id"], "svg": str(svg_path), "csv": str(csv_path), "metadata": str(meta_path)})
    return files
