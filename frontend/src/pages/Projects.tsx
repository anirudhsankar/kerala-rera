import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card, ErrorBox, Loader, Table, fmtDate, fmtInt, type Column } from "../components/ui";
import { useApi, type FilterOptions, type ProjectBrief, type ProjectPage } from "../api";

const LIMIT = 25;
const YEARS = [2026, 2025, 2024, 2023, 2022, 2021];

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <>—</>;
  const cls = status.toLowerCase().includes("progress") ? "inprogress" : status.toLowerCase().includes("complete") ? "completed" : "";
  return <span className={`badge ${cls}`}>{status}</span>;
}

export default function ProjectsPage() {
  const [params] = useSearchParams();
  const urlQ = params.get("q") ?? "";
  const [q, setQ] = useState(urlQ);
  const [district, setDistrict] = useState("");
  const [taluk, setTaluk] = useState("");
  const [village, setVillage] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState<"name" | "newest">("name");
  const [year, setYear] = useState("");
  const [offset, setOffset] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    setQ(urlQ);
    setOffset(0);
  }, [urlQ]);

  const filters = useApi<FilterOptions>("/filters", { district, taluk });
  const { data, error, loading } = useApi<ProjectPage>("/projects", {
    q,
    district,
    taluk,
    village,
    project_type: type,
    project_status: status,
    sort,
    registered_after: year ? `${year}-01-01` : undefined,
    limit: LIMIT,
    offset,
  });

  const reset = (fn: () => void) => {
    setOffset(0);
    fn();
  };

  const columns: Column<ProjectBrief>[] = [
    { key: "project_name", header: "Project", render: (r) => r.project_name ?? "—" },
    { key: "district", header: "District", render: (r) => r.district ?? "—" },
    { key: "taluk", header: "Taluk", render: (r) => r.taluk ?? "—" },
    { key: "village", header: "Village", render: (r) => r.village ?? "—" },
    { key: "project_type", header: "Type", render: (r) => r.project_type ?? "—" },
    { key: "project_status", header: "Status", render: (r) => <StatusBadge status={r.project_status} /> },
    { key: "total_units", header: "Units", align: "right", render: (r) => fmtInt(r.total_units) },
    { key: "certificate_date", header: "Registered", render: (r) => fmtDate(r.certificate_date) },
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
          <select
            value={district}
            onChange={(e) => reset(() => { setDistrict(e.target.value); setTaluk(""); setVillage(""); })}
          >
            <option value="">All districts</option>
            {filters.data?.districts.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select
            value={taluk}
            disabled={!district}
            onChange={(e) => reset(() => { setTaluk(e.target.value); setVillage(""); })}
          >
            <option value="">{district ? "All taluks" : "District first"}</option>
            {filters.data?.taluks?.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select
            value={village}
            disabled={!taluk}
            onChange={(e) => reset(() => setVillage(e.target.value))}
          >
            <option value="">{taluk ? "All villages" : "Taluk first"}</option>
            {filters.data?.villages?.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
          <select value={type} onChange={(e) => reset(() => setType(e.target.value))}>
            <option value="">All types</option>
            {filters.data?.types.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select value={status} onChange={(e) => reset(() => setStatus(e.target.value))}>
            <option value="">All statuses</option>
            {filters.data?.statuses.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select value={year} onChange={(e) => reset(() => setYear(e.target.value))}>
            <option value="">Any registration year</option>
            {YEARS.map((y) => (
              <option key={y} value={String(y)}>Registered {y} or later</option>
            ))}
          </select>
          <select value={sort} onChange={(e) => reset(() => setSort(e.target.value as "name" | "newest"))}>
            <option value="name">Sort: A–Z</option>
            <option value="newest">Sort: newest first</option>
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
