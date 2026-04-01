from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from html import unescape
from pathlib import Path
import os
import re
import subprocess
import urllib.request


ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
OUTPUT_PATH = ASSETS_DIR / "branch-contributions.svg"
DAYS = 365
CELL = 11
GAP = 4
LEFT = 24
TOP = 40
RIGHT = 16
BOTTOM = 30
CORNER = 2
TITLE_Y = 16
MONTH_Y = 28
LEGEND_Y_OFFSET = 20
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
BG = "#0d1117"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
LEVELS = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}
WEEKDAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}
MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
PRUNE_DIRS = {
    ".Trash",
    ".cache",
    ".codex",
    ".npm",
    ".pnpm-store",
    ".vscode",
    "Applications",
    "Desktop",
    "Documents",
    "Downloads",
    "Library",
    "Movies",
    "Music",
    "Pictures",
    "Public",
}


def run_git(repo_path: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo_path), *args], text=True).strip()


def get_username() -> str:
    env_username = os.environ.get("GITHUB_USERNAME")
    if env_username:
        return env_username

    remote = run_git(ROOT, "remote", "get-url", "origin")
    match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$", remote)
    if not match:
        raise RuntimeError("Could not determine GitHub username from origin remote")
    owner, repo = match.groups()
    return owner if repo == owner else owner


def fetch_official_contributions(username: str) -> dict[str, int]:
    url = f"https://github.com/users/{username}/contributions"
    request = urllib.request.Request(url, headers={"User-Agent": "branch-contributions"})
    with urllib.request.urlopen(request) as response:
        html = response.read().decode("utf-8")

    pattern = re.compile(
        r'data-date="(?P<date>\d{4}-\d{2}-\d{2})"[^>]*>.*?</td>\s*<tool-tip[^>]*>(?P<tooltip>.*?)</tool-tip>',
        re.DOTALL,
    )

    counts: dict[str, int] = {}
    for match in pattern.finditer(html):
        day = match.group("date")
        tooltip = unescape(re.sub(r"<[^>]+>", "", match.group("tooltip"))).strip()
        count_match = re.search(r"(\d+)\s+contributions?", tooltip)
        counts[day] = int(count_match.group(1)) if count_match else 0

    if not counts:
        raise RuntimeError("Failed to parse official contributions from GitHub")
    return counts


def iter_repo_roots(scan_root: Path) -> list[Path]:
    repos: list[Path] = []
    seen: set[Path] = set()

    for current_root, dirnames, _ in os.walk(scan_root):
        current = Path(current_root)
        dirnames[:] = [name for name in dirnames if name not in PRUNE_DIRS]

        if ".git" in dirnames:
            resolved = current.resolve()
            if resolved not in seen:
                repos.append(resolved)
                seen.add(resolved)
            dirnames[:] = []

    if ROOT.resolve() not in seen:
        repos.append(ROOT.resolve())
    return sorted(repos)


def get_default_refs(repo_path: Path) -> list[str]:
    refs_output = run_git(repo_path, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes/origin")
    refs = [line.strip() for line in refs_output.splitlines() if line.strip()]

    result = subprocess.run(
        ["git", "-C", str(repo_path), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    origin_head = result.stdout.strip() if result.returncode == 0 else ""

    preferred = [origin_head, "main", "master", "gh-pages", "origin/main", "origin/master", "origin/gh-pages"]
    default_refs = [ref for ref in preferred if ref and ref in refs]
    if not default_refs and refs:
        default_refs = [refs[0]]
    return default_refs


def get_branch_only_counts_for_repo(repo_path: Path) -> Counter[str]:
    default_refs = get_default_refs(repo_path)
    cmd = ["git", "-C", str(repo_path), "log", "--all", "--date=short", "--pretty=format:%ad"]
    if default_refs:
        cmd.append("--not")
        cmd.extend(default_refs)
    output = subprocess.check_output(cmd, text=True)
    return Counter(line.strip() for line in output.splitlines() if line.strip())


def get_branch_only_counts(scan_root: Path) -> tuple[Counter[str], list[Path]]:
    combined: Counter[str] = Counter()
    repos = iter_repo_roots(scan_root)
    for repo_path in repos:
        try:
            combined.update(get_branch_only_counts_for_repo(repo_path))
        except subprocess.CalledProcessError:
            continue
    return combined, repos


def contribution_level(count: int) -> int:
    if count <= 0:
        return 0
    if count < 4:
        return 1
    if count < 8:
        return 2
    if count < 12:
        return 3
    return 4


def build_days(official: dict[str, int], branch_only: Counter[str]) -> list[dict[str, int | date]]:
    end = date.today()
    start = end - timedelta(days=DAYS - 1)
    days: list[dict[str, int | date]] = []
    current = start
    while current <= end:
        key = current.isoformat()
        official_count = official.get(key, 0)
        branch_count = branch_only.get(key, 0)
        total = official_count + branch_count
        days.append(
            {
                "date": current,
                "official": official_count,
                "branch": branch_count,
                "total": total,
                "level": contribution_level(total),
            }
        )
        current += timedelta(days=1)
    return days


def build_month_labels(days: list[dict[str, int | date]]) -> list[str]:
    labels: list[str] = []
    seen_months: set[tuple[int, int]] = set()
    start = days[0]["date"]
    assert isinstance(start, date)
    for item in days:
        day = item["date"]
        assert isinstance(day, date)
        if day.day > 7:
            continue
        key = (day.year, day.month)
        if key in seen_months:
            continue
        seen_months.add(key)
        week = (day - start).days // 7
        x = LEFT + week * (CELL + GAP)
        labels.append(
            f'<text x="{x}" y="{MONTH_Y}" fill="{MUTED}" font-size="10" font-family="{FONT}">{MONTH_LABELS[day.month - 1]}</text>'
        )
    return labels


def build_weekday_labels() -> list[str]:
    labels: list[str] = []
    for row, label in WEEKDAY_LABELS.items():
        y = TOP + row * (CELL + GAP) + 8
        labels.append(
            f'<text x="0" y="{y}" fill="{MUTED}" font-size="10" font-family="{FONT}">{label}</text>'
        )
    return labels


def build_rects(days: list[dict[str, int | date]]) -> list[str]:
    rects: list[str] = []
    start = days[0]["date"]
    assert isinstance(start, date)
    for item in days:
        day = item["date"]
        total = item["total"]
        official = item["official"]
        branch = item["branch"]
        level = item["level"]
        assert isinstance(day, date)
        assert isinstance(total, int)
        assert isinstance(official, int)
        assert isinstance(branch, int)
        assert isinstance(level, int)
        week = (day - start).days // 7
        row = (day.weekday() + 1) % 7
        x = LEFT + week * (CELL + GAP)
        y = TOP + row * (CELL + GAP)
        tooltip = f"{day.isoformat()}: {total} total ({official} official + {branch} branch-only)"
        rects.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{CORNER}" ry="{CORNER}" fill="{LEVELS[level]}">'
            f"<title>{tooltip}</title></rect>"
        )
    return rects


def build_legend(width: int) -> str:
    x = width - RIGHT - 120
    y = TOP + 7 * (CELL + GAP) + LEGEND_Y_OFFSET
    blocks = "".join(
        f'<rect x="{x + 34 + i * 14}" y="{y - 10}" width="10" height="10" rx="2" ry="2" fill="{LEVELS[i]}" />'
        for i in range(5)
    )
    return (
        f'<text x="{x}" y="{y}" fill="{MUTED}" font-size="10" font-family="{FONT}">Less</text>'
        f"{blocks}"
        f'<text x="{x + 34 + 5 * 14 + 4}" y="{y}" fill="{MUTED}" font-size="10" font-family="{FONT}">More</text>'
    )


def render_svg(days: list[dict[str, int | date]], username: str, repo_count: int) -> str:
    weeks = ((len(days) - 1) // 7) + 1
    width = LEFT + weeks * (CELL + GAP) + RIGHT
    height = TOP + 7 * (CELL + GAP) + BOTTOM + 18
    total = sum(int(item["total"]) for item in days)
    branch_total = sum(int(item["branch"]) for item in days)
    official_total = sum(int(item["official"]) for item in days)

    month_labels = "".join(build_month_labels(days))
    weekday_labels = "".join(build_weekday_labels())
    rects = "".join(build_rects(days))
    legend = build_legend(width)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Merged contribution graph for {username}">
  <rect width="100%" height="100%" fill="{BG}"/>
  <text x="0" y="{TITLE_Y}" fill="{TEXT}" font-size="14" font-family="{FONT}">{total} contributions in the last year</text>
  <text x="{width}" y="{TITLE_Y}" text-anchor="end" fill="{MUTED}" font-size="10" font-family="{FONT}">GitHub official + branch-only extras ({branch_total}) across {repo_count} repos</text>
  {month_labels}
  {weekday_labels}
  {rects}
  {legend}
  <text x="0" y="{height - 2}" fill="{MUTED}" font-size="10" font-family="{FONT}">Official: {official_total} | Branch-only added: {branch_total}</text>
</svg>
'''


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    username = get_username()
    scan_root = Path(os.environ.get("BRANCH_SCAN_ROOT", str(Path.home()))).expanduser().resolve()
    official = fetch_official_contributions(username)
    branch_only, repos = get_branch_only_counts(scan_root)
    days = build_days(official, branch_only)
    OUTPUT_PATH.write_text(render_svg(days, username, len(repos)), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Scanned {len(repos)} repos under {scan_root}")


if __name__ == "__main__":
    main()
