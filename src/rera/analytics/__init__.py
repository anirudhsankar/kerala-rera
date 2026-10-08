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
    by_taluk,
    data_quality_summary,
    district_detail,
    filter_options,
    get_project,
    history_summary,
    overview,
    project_changes,
    project_history,
    recent_changes,
    recent_projects,
    runs,
    search_projects,
    taluk_detail,
    taluks_for_district,
    timeline,
    village_detail,
    villages_for,
)

__all__ = [
    "PromoterBuildResult",
    "build_promoters",
    "canonical_key",
    "baseline",
    "builder_detail",
    "by_builder",
    "by_district",
    "by_taluk",
    "data_quality_summary",
    "district_detail",
    "filter_options",
    "get_project",
    "history_summary",
    "overview",
    "project_changes",
    "project_history",
    "recent_changes",
    "recent_projects",
    "runs",
    "search_projects",
    "taluk_detail",
    "taluks_for_district",
    "timeline",
    "village_detail",
    "villages_for",
]
