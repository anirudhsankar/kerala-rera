import { Link, useSearchParams } from "react-router-dom";
import { Card, ErrorBox, Loader, Table, fmtDate, fmtInt, type Column } from "../components/ui";
import { useApi, type ChangeEvent, type ProjectDetail, type Snapshot } from "../api";

export default function ProjectDetailPage() {
  const [params] = useSearchParams();
  const reg = params.get("registration_number") ?? "";
  const detail = useApi<ProjectDetail>("/project", { registration_number: reg });
  const history = useApi<Snapshot[]>("/project/history", { registration_number: reg });
  const changes = useApi<ChangeEvent[]>("/project/changes", { registration_number: reg });

  if (!reg) return <ErrorBox message="No registration number provided" />;
  if (detail.loading) return <Loader />;
  if (detail.error) return <ErrorBox message={detail.error} />;
  if (!detail.data) return <ErrorBox message="Project not found" />;

  const p = detail.data;

  const snapshotColumns: Column<Snapshot>[] = [
    { key: "collected_at", header: "Collected", render: (r) => fmtDate(r.collected_at) },
    { key: "project_status", header: "Status", render: (r) => r.project_status ?? "—" },
    { key: "declared_completion_date", header: "Completion", render: (r) => fmtDate(r.declared_completion_date) },
    { key: "total_units", header: "Units", align: "right", render: (r) => fmtInt(r.total_units) },
    { key: "sold_units", header: "Sold", align: "right", render: (r) => fmtInt(r.sold_units) },
    { key: "source_hash", header: "Source hash", render: (r) => r.source_hash.slice(0, 12) },
  ];
  const changeColumns: Column<ChangeEvent>[] = [
    { key: "detected_at", header: "Detected", render: (r) => fmtDate(r.detected_at) },
    { key: "field_name", header: "Field", render: (r) => r.field_name },
    { key: "old_value", header: "Old", render: (r) => r.old_value ?? "—" },
    { key: "new_value", header: "New", render: (r) => r.new_value ?? "—" },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <h2>{p.project_name ?? "—"}</h2>
          <p className="muted small">
            {p.rera_registration_number}
            {p.promoter_id && (
              <>
                {" · "}
                <Link className="link" to={`/builders/${p.promoter_id}`}>
                  {p.promoter_canonical_name ?? p.promoter_name_raw}
                </Link>
              </>
            )}
          </p>
        </div>
      </div>

      <div className="grid">
        <Card title="Project details">
          <dl className="fields">
            <dt>Registration number</dt>
            <dd>{p.rera_registration_number}</dd>
            <dt>Certificate number</dt>
            <dd>{p.certificate_number ?? "—"}</dd>
            <dt>Promoter (raw)</dt>
            <dd>{p.promoter_name_raw ?? "—"}</dd>
            <dt>Type</dt>
            <dd>{p.project_type ?? "—"}</dd>
            <dt>Status</dt>
            <dd>{p.project_status ?? "—"}</dd>
            <dt>Start date</dt>
            <dd>{fmtDate(p.project_start_date)}</dd>
            <dt>Declared completion</dt>
            <dd>{fmtDate(p.declared_completion_date)}</dd>
            <dt>Certificate date</dt>
            <dd>{fmtDate(p.certificate_date)}</dd>
            <dt>Total units</dt>
            <dd>{fmtInt(p.total_units)}</dd>
            <dt>Sold units</dt>
            <dd>{fmtInt(p.sold_units)}</dd>
            <dt>District / Taluk / Village</dt>
            <dd>
              {p.district ?? "—"} · {p.taluk ?? "—"} · {p.village ?? "—"}
            </dd>
            <dt>First seen</dt>
            <dd>{fmtDate(p.first_seen_at)}</dd>
            <dt>Last checked</dt>
            <dd>{fmtDate(p.last_checked_at)}</dd>
          </dl>
        </Card>

        <Card title="History" subtitle="Immutable snapshots (one per observed change)">
          {history.loading && <Loader />}
          {!history.loading && (
            <Table
              columns={snapshotColumns}
              rows={history.data ?? []}
              rowKey={(r) => r.id}
            />
          )}
        </Card>
      </div>

      <Card title="Detected changes" subtitle="Field-level differences between snapshots">
        {changes.loading && <Loader />}
        {!changes.loading && (changes.data?.length ?? 0) === 0 && (
          <div className="state muted">
            No changes recorded yet. Changes appear as new exports are ingested.
          </div>
        )}
        {!changes.loading && (changes.data?.length ?? 0) > 0 && (
          <Table columns={changeColumns} rows={changes.data ?? []} rowKey={(r) => r.id} />
        )}
      </Card>
    </>
  );
}
