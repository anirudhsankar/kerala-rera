import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { KeralaTalukMap } from "../components/KeralaTalukMap";
import {
  Card,
  ErrorBox,
  Kpi,
  Loader,
  Table,
  fmtDate,
  fmtInt,
  fmtPct,
  type Column,
} from "../components/ui";
import {
  useApi,
  type FilterOptions,
  type ProjectBrief,
  type ProjectPage,
  type TalukDetail,
  type TalukStat,
  type VillageDetail,
  type VillageStat,
} from "../api";

function monthsAgo(n: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() - n);
  return d.toISOString().slice(0, 10);
}

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <>—</>;
  const cls = status.toLowerCase().includes("progress")
    ? "inprogress"
    : status.toLowerCase().includes("complete")
      ? "completed"
      : "";
  return <span className={`badge ${cls}`}>{status}</span>;
}

function TalukOptions({
  district,
  value,
  onChange,
}: {
  district: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const { data } = useApi<TalukStat[]>("/locations/taluks", { district });
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">All taluks</option>
      {(data ?? []).map((t) => (
        <option key={t.taluk} value={t.taluk}>
          {t.taluk} ({t.projects})
        </option>
      ))}
    </select>
  );
}

function VillageOptions({
  district,
  taluk,
  value,
  onChange,
}: {
  district: string;
  taluk: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const { data } = useApi<VillageStat[]>("/locations/villages", { district, taluk });
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">All villages</option>
      {(data ?? []).map((v) => (
        <option key={v.village} value={v.village}>
          {v.village} ({v.projects})
        </option>
      ))}
    </select>
  );
}

function DistrictTalukMap({ district }: { district: string }) {
  const { data, loading } = useApi<TalukStat[]>("/locations/by-taluk", { district });
  if (loading) return <Loader label="Loading taluk map…" />;
  const mapped = (data ?? []).map((t) => ({ name: t.taluk, value: t.projects }));
  return <KeralaTalukMap data={mapped} />;
}

function LocalitySummary({
  district,
  taluk,
  village,
}: {
  district: string;
  taluk: string;
  village: string;
}) {
  const talukQ = useApi<TalukDetail | null>(
    "/locations/taluk",
    { district, taluk },
    Boolean(district && taluk),
  );
  const villageQ = useApi<VillageDetail | null>(
    "/locations/village",
    { district, village, taluk },
    Boolean(village),
  );
  const summary = village ? villageQ.data?.summary : talukQ.data?.summary;
  if (!summary) return null;
  return (
    <div className="kpis">
      <Kpi icon="building" tone="brand" label="Projects" value={fmtInt(summary.projects)} />
      <Kpi icon="home" tone="ocean" label="Units planned" value={fmtInt(summary.total_units)} />
      <Kpi icon="tag" tone="saffron" label="Units sold" value={fmtInt(summary.sold_units)} />
      <Kpi icon="percent" tone="plum" label="Share sold" value={fmtPct(summary.sell_through)} />
    </div>
  );
}

export default function FindPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const district = params.get("district") ?? "";
  const taluk = params.get("taluk") ?? "";
  const village = params.get("village") ?? "";
  const months = Number(params.get("months") ?? "12");

  const filters = useApi<FilterOptions>("/filters");

  const update = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    setParams(next, { replace: true });
  };

  const registeredAfter = useMemo(
    () => (months > 0 ? monthsAgo(months) : undefined),
    [months],
  );

  const results = useApi<ProjectPage>("/projects", {
    district,
    taluk,
    village,
    sort: "newest",
    registered_after: registeredAfter,
    limit: 60,
  });

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

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Find projects</p>
          <h2>New projects near you</h2>
          <p className="muted small">
            Pick your district, taluk and village to see registered projects — newest first.
          </p>
        </div>
      </div>

      <Card>
        <div className="toolbar">
          <select
            value={district}
            onChange={(e) => update({ district: e.target.value, taluk: "", village: "" })}
          >
            <option value="">All districts</option>
            {filters.data?.districts.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>

          {district ? (
            <TalukOptions district={district} value={taluk} onChange={(v) => update({ taluk: v, village: "" })} />
          ) : (
            <select disabled>
              <option>Select a district first</option>
            </select>
          )}

          {district && taluk ? (
            <VillageOptions district={district} taluk={taluk} value={village} onChange={(v) => update({ village: v })} />
          ) : (
            <select disabled>
              <option>Select a taluk first</option>
            </select>
          )}

          <select value={String(months)} onChange={(e) => update({ months: e.target.value })}>
            <option value="6">Registered in last 6 months</option>
            <option value="12">Registered in last 12 months</option>
            <option value="24">Registered in last 24 months</option>
            <option value="0">All time</option>
          </select>
        </div>

        {taluk && <LocalitySummary district={district} taluk={taluk} village={village} />}
      </Card>

      {district && (
        <Card
          title={`Taluks in ${district}`}
          subtitle="Colour shows number of projects · taluks without boundary data appear unshaded"
        >
          <DistrictTalukMap district={district} />
        </Card>
      )}

      <Card
        title={months > 0 ? `Registered in the last ${months} months` : "All registered projects"}
        subtitle={district ? `${district}${taluk ? " · " + taluk : ""}${village ? " · " + village : ""}` : "Across Kerala"}
        right={<span className="muted small">{fmtInt(results.data?.total ?? 0)} projects</span>}
      >
        {results.loading && <Loader />}
        {results.error && <ErrorBox message={results.error} />}
        {!results.loading && !results.error && (
          <Table
            columns={columns}
            rows={results.data?.items ?? []}
            rowKey={(r) => r.rera_registration_number}
            onRowClick={(r) =>
              navigate(`/project?registration_number=${encodeURIComponent(r.rera_registration_number)}`)
            }
          />
        )}
      </Card>
    </>
  );
}
