import { useNavigate, useParams } from "react-router-dom";
import { EChart } from "../components/EChart";
import { Card, ErrorBox, Kpi, Loader, Table, fmtInt, fmtPct, type Column } from "../components/ui";
import { useApi, type BuilderDetail, type ProjectBrief } from "../api";

export default function BuilderDetailPage() {
  const { id = "" } = useParams();
  const { data, error, loading } = useApi<BuilderDetail>(`/builders/${id}`);
  const navigate = useNavigate();

  if (loading) return <Loader />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return <ErrorBox message="Builder not found" />;

  const s = data.summary;
  const columns: Column<ProjectBrief>[] = [
    { key: "project_name", header: "Project", render: (r) => r.project_name ?? "—" },
    { key: "rera_registration_number", header: "Registration", render: (r) => r.rera_registration_number },
    { key: "district", header: "District", render: (r) => r.district ?? "—" },
    { key: "project_type", header: "Type", render: (r) => r.project_type ?? "—" },
    { key: "project_status", header: "Status", render: (r) => r.project_status ?? "—" },
    { key: "total_units", header: "Units", align: "right", render: (r) => fmtInt(r.total_units) },
    { key: "sold_units", header: "Sold", align: "right", render: (r) => fmtInt(r.sold_units) },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Builder</p>
          <h2>
            {data.name} {data.needs_review && <span className="badge review">review</span>}
          </h2>
          <p className="muted small">
            Original spelling preserved for every project. Grouped by name matching.
          </p>
        </div>
      </div>

      <div className="kpis">
        <Kpi icon="building" tone="brand" label="Projects" value={fmtInt(s.projects)} />
        <Kpi icon="home" tone="ocean" label="Units planned" value={fmtInt(s.total_units)} />
        <Kpi icon="tag" tone="saffron" label="Units sold" value={fmtInt(s.sold_units)} />
        <Kpi icon="percent" tone="plum" label="Share sold" value={fmtPct(s.sell_through)} />
        <Kpi icon="clock" tone="slate" label="Completed" value={fmtInt(s.completed)} />
        <Kpi icon="layers" tone="ocean" label="In progress" value={fmtInt(s.inprogress)} />
        <Kpi icon="clock" tone="saffron" label="Past declared completion" value={fmtInt(s.past_due_count)} />
        <Kpi
          icon="percent"
          tone="slate"
          label="Avg days past completion"
          value={s.avg_days_past_completion === null ? "—" : Math.round(s.avg_days_past_completion)}
        />
      </div>

      <div className="grid">
        <Card title="District footprint">
          <EChart
            height={Math.max(260, data.by_district.length * 30)}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 160, right: 30, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: { type: "category", data: [...data.by_district].reverse().map((d) => d.district) },
              series: [
                {
                  type: "bar",
                  data: [...data.by_district].reverse().map((d) => d.count),
                  itemStyle: { color: "#1f6feb" },
                },
              ],
            }}
          />
        </Card>

        <Card title="Project type mix">
          <EChart
            height={Math.max(260, data.by_type.length * 60)}
            option={{
              tooltip: { trigger: "item" },
              legend: { bottom: 0, type: "scroll" },
              series: [
                {
                  type: "pie",
                  radius: ["42%", "70%"],
                  data: data.by_type.map((t) => ({ name: t.type ?? "Unknown", value: t.count })),
                },
              ],
            }}
          />
        </Card>
      </div>

      <Card title="Projects" subtitle="Click a row to open the project">
        <Table
          columns={columns}
          rows={data.projects}
          rowKey={(r) => r.rera_registration_number}
          onRowClick={(r) =>
            navigate(`/project?registration_number=${encodeURIComponent(r.rera_registration_number)}`)
          }
        />
      </Card>
    </>
  );
}
