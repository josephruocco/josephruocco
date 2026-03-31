from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
OUTPUT_PATH = ASSETS_DIR / "branch-contributions.svg"

CELL = 12
GAP = 3
LEFT = 30
TOP = 26
DAYS = 365

WEEKDAY_LABELS = {
    1: "Mon",
    3: "Wed",
    5: "Fri",
}

MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def get_commit_dates(repo_path: Path) -> list[str]:
    output = subprocess.check_output(
        ["git", "-C", str(repo_path), "log", "--all", "--date=short", "--pretty=format:%ad"],
        text=True,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_day_counts(repo_path: Path) -> list[tuple[date, int]]:
    counts = Counter(get_commit_dates(repo_path))
    end = date.today()
    start = end - timedelta(days=DAYS - 1)

    days: list[tuple[date, int]] = []
    current = start
    while current <= end:
        key = current.isoformat()
        days.append((current, counts.get(key, 0)))
        current += timedelta(days=1)
    return days


def level(count: int) -> str:
    if count == 0:
        return "#ebedf0"
    if count == 1:
        return "#9be9a8"
    if count <= 3:
        return "#40c463"
    if count <= 6:
        return "#30a14e"
    return "#216e39"


def build_month_labels(days: list[tuple[date, int]]) -> list[str]:
    labels: list[str] = []
    seen_months: set[tuple[int, int]] = set()
    for day, _ in days:
        if day.day > 7:
            continue
        key = (day.year, day.month)
        if key in seen_months:
            continue
        seen_months.add(key)
        week = (day - days[0][0]).days // 7
        x = LEFT + week * (CELL + GAP)
        month_name = MONTH_LABELS[day.month - 1]
        labels.append(
            f'<text x="{x}" y="16" font-size="10" fill="#57606a" font-family="ui-sans-serif, system-ui, sans-serif">{month_name}</text>'
        )
    return labels


def build_weekday_labels() -> list[str]:
    labels: list[str] = []
    for row, label in WEEKDAY_LABELS.items():
        y = TOP + row * (CELL + GAP) + 9
        labels.append(
            f'<text x="0" y="{y}" font-size="10" fill="#57606a" font-family="ui-sans-serif, system-ui, sans-serif">{label}</text>'
        )
    return labels


def build_rects(days: list[tuple[date, int]]) -> list[str]:
    rects: list[str] = []
    start = days[0][0]
    for day, count in days:
        week = (day - start).days // 7
        row = (day.weekday() + 1) % 7
        x = LEFT + week * (CELL + GAP)
        y = TOP + row * (CELL + GAP)
        rects.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{level(count)}">'
            f"<title>{day.isoformat()}: {count} commits across all branches</title></rect>"
        )
    return rects


def render_svg(days: list[tuple[date, int]]) -> str:
    weeks = ((len(days) - 1) // 7) + 1
    width = LEFT + weeks * (CELL + GAP) + 10
    height = TOP + 7 * (CELL + GAP) + 30

    month_labels = "".join(build_month_labels(days))
    weekday_labels = "".join(build_weekday_labels())
    rects = "".join(build_rects(days))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="Branch contributions over the last 365 days">
  <rect width="100%" height="100%" fill="white"/>
  <text x="{LEFT}" y="12" font-size="12" font-family="ui-sans-serif, system-ui, sans-serif" fill="#24292f">Branch contributions (all branches, last 365 days)</text>
  {month_labels}
  {weekday_labels}
  {rects}
</svg>
"""


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    days = get_day_counts(ROOT)
    OUTPUT_PATH.write_text(render_svg(days), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
