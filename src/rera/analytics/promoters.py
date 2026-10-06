"""Conservative promoter (builder) canonicalisation.

Strategy (deliberately conservative - we never *guess* that two different names
are the same entity):

* A canonical key is derived from a promoter name by trimming, collapsing
  whitespace, upper-casing and stripping punctuation.
* Projects sharing a key share a ``promoters`` row.
* Any key that maps to more than one distinct raw spelling is flagged
  ``needs_review = true`` so a human can adjudicate - it is not auto-merged
  with any other key.

The raw spelling is always preserved on ``projects.promoter_name_raw``.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from rera.database.models import Project, Promoter


def canonical_key(name: str) -> str:
    """Return a normalised, comparable key for a promoter name."""

    text = re.sub(r"\s+", " ", (name or "")).strip().upper()
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class PromoterBuildResult:
    groups: int = 0
    created: int = 0
    updated: int = 0
    projects_linked: int = 0
    needs_review: int = 0
    review_examples: list[dict] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines = [
            "PROMOTER CANONICALISATION",
            f"  Distinct groups:   {self.groups}",
            f"  Promoters created: {self.created}",
            f"  Promoters updated: {self.updated}",
            f"  Projects linked:   {self.projects_linked}",
            f"  Needs review:      {self.needs_review}",
        ]
        for example in self.review_examples[:10]:
            variants = ", ".join(
                f"{name!r} ({count})" for name, count in example["variants"].items()
            )
            lines.append(f"    ? {example['display']!r}: {variants}")
        return lines


def build_promoters(session: Session, *, dry_run: bool = False) -> PromoterBuildResult:
    """Populate ``promoters`` and link ``projects.promoter_id``.

    Idempotent: running twice yields ``created = 0`` and no new links.
    """

    projects = session.execute(select(Project)).scalars().all()

    groups: dict[str, list[Project]] = {}
    for project in projects:
        raw = (project.promoter_name_raw or "").strip()
        if not raw:
            continue
        key = canonical_key(raw)
        if not key:
            continue
        groups.setdefault(key, []).append(project)

    result = PromoterBuildResult(groups=len(groups))
    existing = {
        promoter.normalized_key: promoter
        for promoter in session.execute(select(Promoter)).scalars()
    }

    for key, members in groups.items():
        variants = Counter((p.promoter_name_raw or "").strip() for p in members)
        display_name = variants.most_common(1)[0][0]
        needs_review = len(variants) > 1

        promoter = existing.get(key)
        if promoter is None:
            promoter = Promoter(
                canonical_name=display_name,
                normalized_key=key,
                match_method="normalized_name",
                needs_review=needs_review,
            )
            session.add(promoter)
            session.flush()
            result.created += 1
        else:
            changed = False
            if promoter.canonical_name != display_name:
                promoter.canonical_name = display_name
                changed = True
            if promoter.needs_review != needs_review:
                promoter.needs_review = needs_review
                changed = True
            if changed:
                result.updated += 1

        if needs_review:
            result.needs_review += 1
            if len(result.review_examples) < 20:
                result.review_examples.append(
                    {
                        "normalized_key": key,
                        "display": display_name,
                        "variants": dict(variants),
                    }
                )

        for project in members:
            if project.promoter_id != promoter.id:
                project.promoter_id = promoter.id
                result.projects_linked += 1

    if dry_run:
        session.rollback()
    else:
        session.commit()
    return result
