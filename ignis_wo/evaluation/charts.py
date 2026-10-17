"""Small dependency-free SVG grouped bar charts for the benchmark handoff.

Colours are the validated reference categorical slots (blue, orange), with dark-mode steps under
prefers-color-scheme. Every bar has a <title> for hover, value labels sit above the bars, a legend
names each series, and a missing value is drawn as "n/a" instead of a zero bar.
"""

from xml.sax.saxutils import escape

STYLE = """<style>
.surface{fill:#fcfcfb}.ink{fill:#0b0b0b}.muted{fill:#52514e}.grid{stroke:#e4e3df}
.s1{fill:#2a78d6}.s2{fill:#eb6834}
@media (prefers-color-scheme: dark){.surface{fill:#1a1a19}.ink{fill:#f0efec}.muted{fill:#c3c2b7}
.grid{stroke:#3a3936}.s1{fill:#3987e5}.s2{fill:#d95926}}
text{font-family:system-ui,-apple-system,Segoe UI,sans-serif}
</style>"""
WIDTH, HEIGHT, LEFT, RIGHT, TOP, BOTTOM = 720, 340, 56, 16, 64, 64


def label(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    return f"{value:g}{unit}"


def grouped_bars(title: str, categories: list[str], series: dict[str, list[float | None]], unit: str = "",
                 maximum: float | None = None, note: str = "") -> str:
    values = [value for column in series.values() for value in column if value is not None]
    top = maximum or (max(values) * 1.15 if values else 1)
    plot_width, plot_height = WIDTH - LEFT - RIGHT, HEIGHT - TOP - BOTTOM
    group = plot_width / len(categories)
    bar = min(28, (group * 0.7 - 2 * (len(series) - 1)) / len(series))
    opening = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(title)}">'
    parts = [opening, STYLE, f'<rect class="surface" width="{WIDTH}" height="{HEIGHT}"/>',
             f'<text class="ink" x="{LEFT}" y="24" font-size="15" font-weight="600">{escape(title)}</text>']
    for step in range(5):
        y = TOP + plot_height - plot_height * step / 4
        parts.append(f'<line class="grid" x1="{LEFT}" x2="{WIDTH - RIGHT}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text class="muted" x="{LEFT - 6}" y="{y + 4:.1f}" font-size="11" text-anchor="end">'
                     f'{top * step / 4:.3g}{escape(unit)}</text>')
    legend_x = LEFT
    for number, (name, column) in enumerate(series.items(), 1):
        parts.append(f'<rect class="s{number}" x="{legend_x}" y="36" width="12" height="12" rx="2"/>')
        parts.append(f'<text class="ink" x="{legend_x + 18}" y="46" font-size="12">{escape(name)}</text>')
        legend_x += 18 + 7 * len(name) + 24
        for index, value in enumerate(column):
            x = LEFT + group * index + (group - len(series) * bar - 2 * (len(series) - 1)) / 2 + (bar + 2) * (number - 1)
            text_y = TOP + plot_height - 4
            if value is not None:
                height = plot_height * value / top
                y = TOP + plot_height - height
                text_y = y - 4
                tooltip = escape(f"{name}, {categories[index]}: {label(value, unit)}")
                parts.append(f'<rect class="s{number}" x="{x:.1f}" y="{y:.1f}" width="{bar:.1f}" height="{height:.1f}" '
                             f'rx="3"><title>{tooltip}</title></rect>')
            parts.append(f'<text class="muted" x="{x + bar / 2:.1f}" y="{text_y:.1f}" font-size="10" '
                         f'text-anchor="middle">{escape(label(value, unit))}</text>')
    for index, category in enumerate(categories):
        x = LEFT + group * index + group / 2
        parts.append(f'<text class="ink" x="{x:.1f}" y="{HEIGHT - BOTTOM + 18}" font-size="11" '
                     f'text-anchor="middle">{escape(category)}</text>')
    if note:
        parts.append(f'<text class="muted" x="{LEFT}" y="{HEIGHT - 14}" font-size="11">{escape(note)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
