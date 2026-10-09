import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { EChart } from "../components/EChart";
import {
  Card,
  ErrorBox,
  Kpi,
  Loader,
  PageHeader,
  Segmented,
  Table,
  fmtDate,
  fmtInt,
  type Column,
} from "../components/ui";
import {
  useApi,
  type FilterOptions,
  type OverdueItem,
  type OverduePage,
  type OverdueSummary,
} from "../api";

type Window = "0" | "30" | "90" | "180";

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <>—</>;
  const cls = status.toLowerCase().includes("progress") ? "inprogress" : "";
  return <span className={`badge ${cls}`}>{status}</span>;
}

export default function OverduePage() {
  const [district, setDistrict] = useState("");
  const [window, setWindow] = useState<Window>("0");
  const navigate = useNavigate();

  const minDays = Number(window);
  const summary = useApi<OverdueSummary>("/overdue/summary", { min_days: minDays });
  const list = useApi<OverduePage>("/overdue", { district, min_days: minDays, limit: 100 });
  const filters = useApi<FilterOptions>("/filters");

  if (summary.loading) return <Loader label="Loading projects past their declared completion…" />;
  if (summary.error) return <ErrorBox message={summary.error} />;
  const s = summary.data!;
  const worst = s.by_district[0];

  const columns: Column<OverdueItem>[] = [
    { key: "project_name", header: "Project", render: (r) => r.project_name ?? "—" },
    { key: "district", header: "District", render: (r) => r.district ?? "—" },
    { key: "taluk", header: "Taluk", render: (r) => r.taluk ?? "—" },
    { key: "declared_completion_date", header: "Declared completion", render: (r) => fmtDate(r.declared_completion_date) },
    {
      key: "days_past_completion",
      header: "Days past",
      align: "right",
      render: (r) => fmtInt(r.days_past_completion),
    },
    { key: "project_status", header: "Status", render: (r) => <StatusBadge status={r.project_status} /> },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Past completion"
        title="Projects past their declared completion"
        subtitle={`Projects whose declared completion date has passed and are not marked Completed · as of ${fmtDate(s.as_of)}`}
        right={
          <Segmented<Window>
            label="Overdue by"
            value={window}
            onChange={setWindow}
            options={[
              { value: "0", label: "All" },
              { value: "30", label: "30d+" },
              { value: "90", label: "90d+" },
              { value: "180", label: "180d+" },
            ]}
          />
        }
      />

      <div className="kpis">
        <Kpi icon="clock" tone="saffron" label="Projects past date" value={fmtInt(s.total)} />
        <Kpi
          icon="percent"
          tone="slate"
          label="Average days past"
          value={s.avg_days_past_completion === null ? "—" : Math.round(s.avg_days_past_completion)}
        />
        <Kpi
          icon="building"
          tone="ocean"
          label="Most affected district"
          value={worst?.district ?? "—"}
          hint={worst ? `${fmtInt(worst.count)} projects` : undefined}
        />
      </div>

      <div className="grid">
        <Card title="Projects past date by district" subtitle="Count of non-completed projects">
          <EChart
            height={330}
            option={{
              tooltip: {
                trigger: "axis",
                formatter: (params: any) => {
                  const p = params[0];
                  const row = s.by_district[p.dataIndex];
                  return `${p.name}<br/>Projects: ${p.value}<br/>Avg days: ${row.avg_days}`;
                },
              },
              grid: { left: 120, right: 24, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: { type: "category", data: [...s.by_district].reverse().map((d) => d.district) },
              series: [
                {
                  type: "bar",
                  data: [...s.by_district].reverse().map((d) => d.count),
                  itemStyle: { color: "#c2410c", borderRadius: [0, 3, 3, 0] },
                },
              ],
            }}
          />
        </Card>

        <Card title="Promoters with the most overdue projects" subtitle="Count and average days past">
          <Table
            columns={[
              { key: "name", header: "Promoter" },
              { key: "count", header: "Projects", align: "right", render: (r) => fmtInt(r.count) },
              { key: "avg_days", header: "Avg days", align: "right", render: (r) => r.avg_days },
            ]}
            rows={s.by_promoter}
            rowKey={(r) => r.promoter_id}
            onRowClick={(r) => navigate(`/builders/${r.promoter_id}`)}
          />
        </Card>
      </div>

      <Card title="Projects" subtitle="Sorted by days past declared completion">
        <div className="toolbar">
          <select value={district} onChange={(e) => setDistrict(e.target.value)}>
            <option value="">All districts</option>
            {filters.data?.districts.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
        {list.loading && <Loader />}
        {list.error && <ErrorBox message={list.error} />}
        {!list.loading && !list.error && (
          <Table
            columns={columns}
            rows={list.data?.items ?? []}
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
