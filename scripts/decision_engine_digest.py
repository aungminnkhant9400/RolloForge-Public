#!/usr/bin/env python3
"""Generate a weekly decision-engine digest for RolloForge.

This turns bookmark intake into a short operator report:
- top themes
- top 3 build/test candidates
- items to ignore for now
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/home/ubuntu/RolloForge")
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
CACHE_DIR = PROJECT_ROOT / ".cache" / "decision-engine"
HISTORY_DIR = REPORTS_DIR / "history" / "decision-engine"


@dataclass
class Candidate:
    bookmark_id: str
    title: str
    url: str
    bucket: str
    priority: float
    worth: float
    tags: list[str]
    reason: str
    summary: str
    created_at: str
    action_score: float = 0.0


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def build_candidates(days: int) -> tuple[list[Candidate], dict[str, Any]]:
    bookmarks = load_json(DATA_DIR / "bookmarks_raw.json")
    analyses = load_json(DATA_DIR / "analysis_results.json")
    by_analysis = {a["bookmark_id"]: a for a in analyses}
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

    candidates: list[Candidate] = []
    tag_counter: Counter[str] = Counter()
    bucket_counter: Counter[str] = Counter()
    theme_groups: dict[str, list[Candidate]] = defaultdict(list)

    for b in bookmarks:
        dt = parse_dt(b.get("bookmarked_at") or b.get("created_at"))
        if not dt or dt < cutoff:
            continue
        analysis = by_analysis.get(b["id"])
        if not analysis:
            continue
        candidate = Candidate(
            bookmark_id=b["id"],
            title=b.get("title") or b.get("text", "")[:80],
            url=b.get("url", ""),
            bucket=analysis.get("recommendation_bucket", "archive"),
            priority=float(analysis.get("priority_score", 0) or 0),
            worth=float(analysis.get("worth_score", 0) or 0),
            tags=list(analysis.get("tags") or b.get("tags") or []),
            reason=analysis.get("recommendation_reason", ""),
            summary=analysis.get("summary", ""),
            created_at=b.get("bookmarked_at") or b.get("created_at") or "",
        )
        candidates.append(candidate)
        bucket_counter[candidate.bucket] += 1
        for tag in candidate.tags:
            if tag and tag != "general":
                tag_counter[tag] += 1
                theme_groups[tag].append(candidate)

    meta = {
        "total": len(candidates),
        "buckets": dict(bucket_counter),
        "top_tags": tag_counter.most_common(8),
    }
    return candidates, meta


def _normalized_title(title: str) -> str:
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return title


SEEN_PATH = CACHE_DIR / "recently-shown.json"


def load_recently_shown(days_back: int = 7) -> set[str]:
    """Load bookmark IDs that appeared in recent digests."""
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        cutoff = (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_back)).isoformat()
        return {item["id"] for item in data if item.get("shown_at", "") > cutoff}
    except Exception:
        return set()


def save_shown(candidate_ids: list[str]) -> None:
    """Record which items were shown today."""
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).replace(tzinfo=None).isoformat()
    entries = [{"id": cid, "shown_at": now} for cid in candidate_ids]
    try:
        existing = json.loads(SEEN_PATH.read_text(encoding="utf-8")) if SEEN_PATH.exists() else []
        # Keep last 30 days only
        cutoff = (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)).isoformat()
        existing = [e for e in existing if e.get("shown_at", "") > cutoff]
        existing.extend(entries)
        SEEN_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        SEEN_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _action_score(candidate: Candidate, recently_shown: set[str]) -> float:
    text = f"{candidate.title} {candidate.reason} {candidate.summary}".lower()
    score = candidate.priority + (0.35 * candidate.worth)
    bonus_terms = {
        'openclaw': 1.2,
        'kimi': 1.0,
        'qwen': 0.8,
        'nnunet': 1.0,
        'gpu': 0.8,
        'automation': 0.7,
        'trading': 0.6,
        'medical-imaging': 0.8,
    }
    for tag, bonus in bonus_terms.items():
        if tag in candidate.tags:
            score += bonus
    if any(word in text for word in ('blocked', 'duplicate', 'already covered', 'thin content')):
        score -= 2.5
    if any(word in text for word in ('directly actionable', 'why now', 'immediate value', 'perfect timing')):
        score += 0.8
    # Penalize recently shown items heavily
    if candidate.bookmark_id in recently_shown:
        score -= 5.0  # Strong penalty so they drop out of top 3
    return round(score, 2)


def rank_top_candidates(candidates: list[Candidate], limit: int = 3) -> list[Candidate]:
    recently_shown = load_recently_shown(days_back=7)
    preferred = [c for c in candidates if c.bucket in {"test_this_week", "build_later"}]
    for c in preferred:
        c.action_score = _action_score(c, recently_shown)
    preferred.sort(key=lambda c: (c.action_score, c.priority, c.worth), reverse=True)
    deduped: list[Candidate] = []
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    for c in preferred:
        title_key = _normalized_title(c.title)
        if title_key in seen_titles or c.url in seen_urls:
            continue
        seen_titles.add(title_key)
        seen_urls.add(c.url)
        deduped.append(c)
        if len(deduped) >= limit:
            break
    # Record what we're showing
    save_shown([c.bookmark_id for c in deduped])
    return deduped


def build_report(days: int) -> str:
    candidates, meta = build_candidates(days)
    top = rank_top_candidates(candidates, limit=3)

    top_tags = ", ".join(tag for tag, _ in meta["top_tags"][:5]) or "none"
    lines = []
    lines.append(f"# RolloForge Decision Engine Digest ({days}d)")
    lines.append("")
    lines.append(f"- Items reviewed: **{meta['total']}**")
    lines.append(f"- Buckets: **{meta['buckets']}**")
    lines.append(f"- Top themes: **{top_tags}**")
    lines.append("")
    lines.append("## Top 3 build/test candidates")
    lines.append("")
    if not top:
        lines.append("No strong candidates found.")
    else:
        for i, c in enumerate(top, 1):
            lines.append(f"### {i}. {c.title}")
            lines.append(f"- Bucket: `{c.bucket}`")
            lines.append(f"- Priority: **{c.priority:.1f}** | Worth: **{c.worth:.1f}** | Action score: **{c.action_score:.1f}**")
            if c.tags:
                lines.append(f"- Tags: {', '.join(c.tags)}")
            if c.reason:
                lines.append(f"- Why now: {c.reason}")
            lines.append(f"- URL: {c.url}")
            lines.append("")

    archive_count = sum(1 for c in candidates if c.bucket == "archive")
    ignore_count = sum(1 for c in candidates if c.bucket == "ignore")
    lines.append("## Operator take")
    lines.append("")
    lines.append(
        f"The intake machine is now clean enough to use as a decision surface. Focus on the 3 candidates above, ignore the {ignore_count} low-signal items, and treat the {archive_count} archive items as reference only."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    report = build_report(args.days)
    print(report)

    if args.save:
        out_dir = HISTORY_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"decision-engine-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
