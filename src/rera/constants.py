"""Shared constants and controlled vocabularies used across the pipeline.

These vocabularies are *illustrative* unless confirmed against the official
K-RERA export. Because the live site is protected by an anti-bot challenge
(see ``docs/source-inspection.md``), the exact status/type strings could not be
confirmed. Unknown values are therefore *flagged*, never silently dropped.
"""

from __future__ import annotations

# --- Ingestion run lifecycle -------------------------------------------------
RUN_STATUS_RUNNING = "RUNNING"
RUN_STATUS_SUCCESS = "SUCCESS"
RUN_STATUS_PARTIAL = "PARTIAL"
RUN_STATUS_FAILED = "FAILED"
RUN_STATUSES = (
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    RUN_STATUS_PARTIAL,
    RUN_STATUS_FAILED,
)

# --- Data quality severities -------------------------------------------------
SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_ERROR = "ERROR"
SEVERITIES = (SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ERROR)

# --- Collection methods ------------------------------------------------------
COLLECTION_METHOD_FILE = "official_export_file_import"
COLLECTION_METHOD_HTTP = "http_fetch"

# --- Canonical source fields -------------------------------------------------
# The fields we read from an official K-RERA export. Raw values are preserved
# in the snapshot's ``raw_record`` JSON before normalisation.
SOURCE_FIELDS = (
    "rera_registration_number",
    "project_name",
    "promoter_name",
    "project_type",
    "project_status",
    "project_start_date",
    "declared_completion_date",
    "certificate_number",
    "certificate_date",
    "last_modified_date",
    "total_units",
    "sold_units",
    "district",
    "taluk",
    "village",
    "source_url",
)

REQUIRED_FIELDS = ("rera_registration_number", "project_name")

# Fields included in the deterministic source hash and change comparison.
# ``source_url`` is excluded because it is derived / non-substantive.
TRACKED_FIELDS = (
    "rera_registration_number",
    "project_name",
    "promoter_name",
    "project_type",
    "project_status",
    "project_start_date",
    "declared_completion_date",
    "certificate_number",
    "certificate_date",
    "last_modified_date",
    "total_units",
    "sold_units",
    "district",
    "taluk",
    "village",
)

# --- Kerala districts --------------------------------------------------------
KERALA_DISTRICTS = (
    "Thiruvananthapuram",
    "Kollam",
    "Pathanamthitta",
    "Alappuzha",
    "Kottayam",
    "Idukki",
    "Ernakulam",
    "Thrissur",
    "Palakkad",
    "Malappuram",
    "Kozhikode",
    "Wayanad",
    "Kannur",
    "Kasaragod",
)

DISTRICT_ALIASES = {
    "trivandrum": "Thiruvananthapuram",
    "thiruvananthapuram": "Thiruvananthapuram",
    "quilon": "Kollam",
    "kollam": "Kollam",
    "pathanamthitta": "Pathanamthitta",
    "alleppey": "Alappuzha",
    "alappuzha": "Alappuzha",
    "kottayam": "Kottayam",
    "idukki": "Idukki",
    "ernakulam": "Ernakulam",
    "cochin": "Ernakulam",
    "kochi": "Ernakulam",
    "trichur": "Thrissur",
    "thrissur": "Thrissur",
    "palghat": "Palakkad",
    "palakkad": "Palakkad",
    "malappuram": "Malappuram",
    "calicut": "Kozhikode",
    "kozhikode": "Kozhikode",
    "wayanad": "Wayanad",
    "cannanore": "Kannur",
    "kannur": "Kannur",
    "kasargod": "Kasaragod",
    "kasaragod": "Kasaragod",
}

# --- Project status vocabulary ----------------------------------------------
# "Inprogress" and "Completed" are confirmed values in the official K-RERA
# export; the others are retained as plausible/illustrative alternatives.
KNOWN_PROJECT_STATUSES = (
    "Registered",
    "Ongoing",
    "Inprogress",
    "Completed",
    "Lapsed",
    "Revoked",
    "Cancelled",
    "Expired",
    "Rejected",
    "Withdrawn",
)

STATUS_ALIASES = {
    "registered": "Registered",
    "ongoing": "Ongoing",
    "in progress": "Ongoing",
    "under construction": "Ongoing",
    "completed": "Completed",
    "complete": "Completed",
    "lapsed": "Lapsed",
    "revoked": "Revoked",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "expired": "Expired",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
}

# --- Project type vocabulary -------------------------------------------------
# The five compound values are confirmed from the official K-RERA export and
# are stored verbatim (source-preserving). Generic values are retained too.
KNOWN_PROJECT_TYPES = (
    "Residential",
    "Commercial",
    "Mixed",
    "Plotted",
    "Plots",
    "Apartment",
    "Villa",
    "Industrial",
    "Others",
    "Residential (Apartment)",
    "Villas (Plots & Buildings)",
    "Mixed (Commercial & Residential)",
    "Shops/Office Space (Commercial)",
)

PROJECT_TYPE_ALIASES = {
    "residential": "Residential",
    "apartment": "Apartment",
    "apartments": "Apartment",
    "flat": "Apartment",
    "flats": "Apartment",
    "commercial": "Commercial",
    "mixed": "Mixed",
    "mixed use": "Mixed",
    "mixed use development": "Mixed",
    "plotted": "Plotted",
    "plot": "Plots",
    "plots": "Plots",
    "villa": "Villa",
    "villas": "Villa",
    "industrial": "Industrial",
    "others": "Others",
    "other": "Others",
}
