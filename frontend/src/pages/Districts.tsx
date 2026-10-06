import { useNavigate } from "react-router-dom";
import { EChart } from "../components/EChart";
import { KeralaMap } from "../components/KeralaMap";
import { Card, ErrorBox, Loader, Table, fmtInt, fmtPct, type Column } from "../components/ui";
import { useApi, type DistrictStat } from "../api";

export default function DistrictsPage() {
  const { data, error, loading } = useApi<DistrictStat[]>("/districts");
  const navigate = useNavigate();

  if (loading) return <Loader />;
  if (error) return <ErrorBox message={error} />;
  const rows = data ?? [];

  const mapData = rows
    .filter((d) => d.district)
    .map((d) => ({ name: d.district as string, value: d.projects }));

  const byProjects = [...rows].sort((a, b) => a.projects - b.projects);

  const columns: Column<DistrictStat>[] = [
    { key: "district", header: "District", render: (r) => r.district ?? "—" },
    { key: "projects", header: "Projects", align: "right", render: (r) => fmtInt(r.projects) },
    { key: "total_units", header: "Units", align: "right", render: (r) => fmtInt(r.total_units) },
    { key: "sold_units", header: "Sold", align: "right", render: (r) => fmtInt(r.sold_units) },
    { key: "sell_through", header: "Sell-through", align: "right", render: (r) => fmtPct(r.sell_through) },
    { key: "completed", header: "Completed", align: "right", render: (r) => fmtInt(r.completed) },
    { key: "inprogress", header: "In progress", align: "right", render: (r) => fmtInt(r.inprogress) },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Districts</p>
          <h2>Development across Kerala</h2>
          <p className="muted small">Tap any district to see its projects, taluks and top builders.</p>
        </div>
      </div>

      <Card title="Projects by district" subtitle="Bigger colour = more registered projects">
        <KeralaMap data={mapData} metric="projects" />
      </Card>

      <div className="grid">
        <Card title="Projects by district" subtitle="Sorted">
          <EChart
            height={360}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 150, right: 24, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: { type: "category", data: byProjects.map((d) => d.district ?? "Unknown") },
              series: [
                {
                  type: "bar",
                  data: byProjects.map((d) => d.projects),
                  itemStyle: { color: "#1f6feb" },
                },
              ],
            }}
          />
        </Card>

        <Card title="Sell-through by district" subtitle="Sold ÷ total units (projects with unit data)">
          <EChart
            height={360}
            option={{
              tooltip: {
                trigger: "axis",
                valueFormatter: (value: any) =>
                  typeof value === "number" ? `${(value * 100).toFixed(1)}%` : String(value),
              },
              grid: { left: 150, right: 24, top: 10, bottom: 20 },
              xAxis: { type: "value", axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
              yAxis: { type: "category", data: byProjects.map((d) => d.district ?? "Unknown") },
              series: [
                {
                  type: "bar",
                  data: byProjects.map((d) => d.sell_through ?? 0),
                  itemStyle: { color: "#2f9e6b" },
                },
              ],
            }}
          />
        </Card>
      </div>

      <Card title="District statistics">
        <Table
          columns={columns}
          rows={rows}
          rowKey={(r) => r.district ?? "unknown"}
          onRowClick={(r) => r.district && navigate(`/districts/${encodeURIComponent(r.district)}`)}
        />
      </Card>    </>
  );
}
