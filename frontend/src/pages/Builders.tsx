import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { EChart } from "../components/EChart";
import { Card, ErrorBox, Kpi, Loader, Table, fmtInt, fmtPct, type Column } from "../components/ui";
import { useApi, type BuilderStat } from "../api";

type SortKey = "projects" | "total_units" | "sold_units" | "districts";

export default function BuildersPage() {
  const [sort, setSort] = useState<SortKey>("projects");
  const { data, error, loading } = useApi<BuilderStat[]>("/builders", { limit: 200, sort });
  const navigate = useNavigate();

  if (loading) return <Loader />;
  if (error) return <ErrorBox message={error} />;
  const rows = data ?? [];

  const top15 = rows.slice(0, 15);
  const totalProjects = rows.reduce((acc, r) => acc + r.projects, 0);
  const top10 = rows.slice(0, 10).reduce((acc, r) => acc + r.projects, 0);
  const concentration = totalProjects ? top10 / totalProjects : null;

  const columns: Column<BuilderStat>[] = [
    {
      key: "name",
      header: "Builder",
      render: (r) => (
        <>
          {r.name} {r.needs_review && <span className="badge review">review</span>}
        </>
      ),
    },
    { key: "projects", header: "Projects", align: "right", render: (r) => fmtInt(r.projects) },
    { key: "total_units", header: "Units", align: "right", render: (r) => fmtInt(r.total_units) },
    { key: "sold_units", header: "Sold", align: "right", render: (r) => fmtInt(r.sold_units) },
    { key: "sell_through", header: "Sell-through", align: "right", render: (r) => fmtPct(r.sell_through) },
    { key: "districts", header: "Districts", align: "right", render: (r) => fmtInt(r.districts) },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Builders</p>
          <h2>Who's building Kerala?</h2>
          <p className="muted small">
            Promoter names are grouped by a normalised spelling; uncertain groups
            are flagged for review.
          </p>
        </div>
        <div className="toolbar">
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
            <option value="projects">Sort by projects</option>
            <option value="total_units">Sort by units</option>
            <option value="sold_units">Sort by sold units</option>
            <option value="districts">Sort by districts</option>
          </select>
        </div>
      </div>

      <div className="kpis">
        <Kpi icon="building" tone="brand" label="Builders" value={fmtInt(rows.length)} />
        <Kpi icon="percent" tone="plum" label="Top-10 share" value={fmtPct(concentration)} hint="of all projects" />
        <Kpi
          icon="home"
          tone="saffron"
          label="Most active builder"
          value={rows[0]?.name ?? "—"}
          hint={`${fmtInt(rows[0]?.projects)} projects`}
        />
      </div>

      <Card title="Top 15 builders" subtitle={`By ${sort.replace("_", " ")}`}>
        <EChart
          height={Math.max(320, top15.length * 34)}
          option={{
            tooltip: { trigger: "axis" },
            grid: { left: 260, right: 40, top: 10, bottom: 20 },
            xAxis: { type: "value" },
            yAxis: { type: "category", data: [...top15].reverse().map((b) => b.name) },
            series: [
              {
                type: "bar",
                data: [...top15].reverse().map((b) => (b as any)[sort]),
                itemStyle: { color: "#1f6feb" },
              },
            ],
          }}
        />
      </Card>

      <Card title="Builder leaderboard" subtitle="Click a row for detail">
        <Table
          columns={columns}
          rows={rows}
          rowKey={(r) => r.promoter_id}
          onRowClick={(r) => navigate(`/builders/${r.promoter_id}`)}
        />
      </Card>
    </>
  );
}
