import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { EChart } from "../components/EChart";
import { Card, ErrorBox, Kpi, Loader, Table, fmtDate, fmtInt, type Column } from "../components/ui";
import {
  useApi,
  type ChangeEventPage,
  type ChangeRow,
  type FilterOptions,
  type HistorySummary,
} from "../api";

const FIELD_LABELS: Record<string, string> = {
  declared_completion_date: "Declared completion date",
  sold_units: "Sold units",
  total_units: "Total units",
  project_status: "Project status",
  project_name: "Project name",
  promoter_name: "Promoter",
  project_type: "Project type",
  project_start_date: "Start date",
  certificate_date: "Certificate date",
  district: "District",
  taluk: "Taluk",
  village: "Village",
};

export default function HistoryPage() {
  const [district, setDistrict] = useState("");
  const [taluk, setTaluk] = useState("");
  const [field, setField] = useState("");
  const navigate = useNavigate();

  const summary = useApi<HistorySummary>("/history/summary");
  const districts = useApi<FilterOptions>("/filters");
  const taluks = useApi<FilterOptions>("/filters", { district }, Boolean(district));
  const changes = useApi<ChangeEventPage>("/changes", {
    district,
    taluk,
    field_name: field,
    limit: 100,
  });

  if (summary.loading) return <Loader label="Loading history…" />;
  if (summary.error) return <ErrorBox message={summary.error} />;
  const s = summary.data!;

  const columns: Column<ChangeRow>[] = [
    { key: "detected_at", header: "Detected", render: (r) => fmtDate(r.detected_at) },
    {
      key: "project",
      header: "Project",
      render: (r) => (
        <a
          className="link"
          href={`/project?registration_number=${encodeURIComponent(r.rera_registration_number)}`}
          onClick={(e) => {
            e.preventDefault();
            navigate(`/project?registration_number=${encodeURIComponent(r.rera_registration_number)}`);
          }}
        >
          {r.project_name ?? r.rera_registration_number}
        </a>
      ),
    },
    { key: "district", header: "District", render: (r) => r.district ?? "—" },
    { key: "taluk", header: "Taluk", render: (r) => r.taluk ?? "—" },
    {
      key: "field_name",
      header: "Field",
      render: (r) => FIELD_LABELS[r.field_name] ?? r.field_name,
    },
    { key: "old_value", header: "From", render: (r) => r.old_value ?? "—" },
    { key: "new_value", header: "To", render: (r) => r.new_value ?? "—" },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">History</p>
          <h2>How projects have changed</h2>
          <p className="muted small">
            Snapshots and field-level changes are recorded on every ingestion. History
            begins {s.baseline_at ? fmtDate(s.baseline_at) : "at the baseline"}.
          </p>
        </div>
      </div>

      <div className="kpis">
        <Kpi icon="layers" tone="brand" label="Recorded changes" value={fmtInt(s.total_changes)} />
        <Kpi icon="building" tone="ocean" label="Projects changed" value={fmtInt(s.projects_changed)} />
        <Kpi icon="clock" tone="slate" label="Baseline" value={fmtDate(s.baseline_at)} />
        <Kpi
          icon="percent"
          tone="plum"
          label="Snapshot months"
          value={fmtInt(s.snapshots_by_month.length)}
        />
      </div>

      {s.total_changes === 0 && (
        <div className="provenance" style={{ marginBottom: 18 }}>
          <strong>No changes recorded yet.</strong> {s.note} As soon as a newer export
          is ingested, differences (declared completion dates, sold units, status, …)
          will appear here and in each project's history.
        </div>
      )}

      <div className="grid">
        <Card title="Changes over time" subtitle="Detected per month">
          <EChart
            height={300}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 46, right: 20, top: 20, bottom: 34 },
              xAxis: { type: "category", data: s.changes_by_month.map((d) => d.period) },
              yAxis: { type: "value" },
              series: [
                {
                  type: "bar",
                  data: s.changes_by_month.map((d) => d.count),
                  itemStyle: { borderRadius: [6, 6, 0, 0], color: "#0ea5e9" },
                },
              ],
            }}
          />
        </Card>

        <Card title="What changed" subtitle="Changes by field">
          <EChart
            height={300}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 170, right: 24, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: {
                type: "category",
                data: [...s.changes_by_field].reverse().map((d) => FIELD_LABELS[d.field_name] ?? d.field_name),
              },
              series: [
                {
                  type: "bar",
                  data: [...s.changes_by_field].reverse().map((d) => d.count),
                  itemStyle: { borderRadius: [0, 6, 6, 0], color: "#7c3aed" },
                },
              ],
            }}
          />
        </Card>
      </div>

      <Card title="Change feed" subtitle="Most recent first">
        <div className="toolbar">
          <select
            value={district}
            onChange={(e) => {
              setDistrict(e.target.value);
              setTaluk("");
            }}
          >
            <option value="">All districts</option>
            {districts.data?.districts.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select value={taluk} disabled={!district} onChange={(e) => setTaluk(e.target.value)}>
            <option value="">{district ? "All taluks" : "District first"}</option>
            {taluks.data?.taluks?.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select value={field} onChange={(e) => setField(e.target.value)}>
            <option value="">All fields</option>
            {s.changes_by_field.map((d) => (
              <option key={d.field_name} value={d.field_name}>
                {FIELD_LABELS[d.field_name] ?? d.field_name}
              </option>
            ))}
          </select>
        </div>

        {changes.loading && <Loader />}
        {changes.error && <ErrorBox message={changes.error} />}
        {!changes.loading && !changes.error && (
          <Table
            columns={columns}
            rows={changes.data?.items ?? []}
            rowKey={(r) => r.id}
          />
        )}
      </Card>

      {s.status_transitions.length > 0 && (
        <Card title="Status transitions" subtitle="Project status before → after">
          <div className="pills">
            {s.status_transitions.map((t, i) => (
              <span className="pill" key={i}>
                <span className="dot" />
                {t.from ?? "—"} → {t.to ?? "—"} · {t.count}
              </span>
            ))}
          </div>
        </Card>
      )}
    </>
  );
}
