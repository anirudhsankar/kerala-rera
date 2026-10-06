"""Analytics package: read-only queries and promoter identity.

Nothing here writes to the source data tables; the only mutation is the
explicit promoter canonicalisation build (``promoters.build_promoters``).
"""

from rera.analytics.promoters import (
    PromoterBuildResult,
    build_promoters,
    canonical_key,
)
from rera.analytics.queries import (
    baseline,
    builder_detail,
    by_builder,
    by_district,
    data_quality_summary,
    district_detail,
    filter_options,
    get_project,
    overview,
    project_changes,
    project_history,
    runs,
    search_projects,
    timeline,
)

__all__ = [
    "PromoterBuildResult",
    "build_promoters",
    "canonical_key",
    "baseline",
    "builder_detail",
    "by_builder",
    "by_district",
    "data_quality_summary",
    "district_detail",
    "filter_options",
    "get_project",
    "overview",
    "project_changes",
    "project_history",
    "runs",
    "search_projects",
    "timeline",
]
