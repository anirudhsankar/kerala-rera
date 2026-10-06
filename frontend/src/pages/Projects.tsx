import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, ErrorBox, Loader, Table, fmtDate, fmtInt, type Column } from "../components/ui";
import { useApi, type FilterOptions, type ProjectBrief, type ProjectPage } from "../api";

const LIMIT = 25;

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <>—</>;
  const cls = status.toLowerCase().includes("progress") ? "inprogress" : status.toLowerCase().includes("complete") ? "completed" : "";
  return <span className={`badge ${cls}`}>{status}</span>;
}

export default function ProjectsPage() {
  const [q, setQ] = useState("");
  const [district, setDistrict] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const navigate = useNavigate();

  const filters = useApi<FilterOptions>("/filters");
  const { data, error, loading } = useApi<ProjectPage>("/projects", {
    q,
    district,
    project_type: type,
    project_status: status,
    limit: LIMIT,
    offset,
  });

  const reset = (fn: () => void) => {
    setOffset(0);
    fn();
  };

  const columns: Column<ProjectBrief>[] = [
    { key: "project_name", header: "Project", render: (r) => r.project_name ?? "—" },
    { key: "rera_registration_number", header: "Registration", render: (r) => r.rera_registration_number },
    { key: "district", header: "District", render: (r) => r.district ?? "—" },
    { key: "project_type", header: "Type", render: (r) => r.project_type ?? "—" },
    { key: "project_status", header: "Status", render: (r) => <StatusBadge status={r.project_status} /> },
    { key: "total_units", header: "Units", align: "right", render: (r) => fmtInt(r.total_units) },
    { key: "sold_units", header: "Sold", align: "right", render: (r) => fmtInt(r.sold_units) },
    { key: "declared_completion_date", header: "Completion", render: (r) => fmtDate(r.declared_completion_date) },
  ];

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Explore</p>
          <h2>Every registered project</h2>
          <p className="muted small">{fmtInt(total)} projects match your filters</p>
        </div>
      </div>

      <Card>
        <div className="toolbar">
          <input
            placeholder="Search name, registration, promoter…"
            value={q}
            onChange={(e) => reset(() => setQ(e.target.value))}
          />
          <select value={district} onChange={(e) => reset(() => setDistrict(e.target.value))}>
            <option value="">All districts</option>
            {filters.data?.districts.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <select value={type} onChange={(e) => reset(() => setType(e.target.value))}>
            <option value="">All types</option>
            {filters.data?.types.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select value={status} onChange={(e) => reset(() => setStatus(e.target.value))}>
            <option value="">All statuses</option>
            {filters.data?.statuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {loading && <Loader />}
        {error && <ErrorBox message={error} />}
        {!loading && !error && (
          <>
            <Table
              columns={columns}
              rows={rows}
              rowKey={(r) => r.rera_registration_number}
              onRowClick={(r) =>
                navigate(`/project?registration_number=${encodeURIComponent(r.rera_registration_number)}`)
              }
            />
            <div className="pager">
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>
                ← Prev
              </button>
              <span>
                {offset + 1}–{Math.min(offset + LIMIT, total)} of {fmtInt(total)}
              </span>
              <button disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)}>
                Next →
              </button>
            </div>
          </>
        )}
      </Card>
    </>
  );
}
