import { useState } from "react";
import { EChart } from "../components/EChart";
import { KeralaMap } from "../components/KeralaMap";
import { KeralaTalukMap } from "../components/KeralaTalukMap";
import { Card, ErrorBox, Kpi, Loader, PageHeader, Segmented, fmtInt, fmtPct } from "../components/ui";
import {
  useApi,
  type Concentration,
  type DistrictStat,
  type PipelineYear,
  type ProjectMix,
  type RegistrationTrend,
  type TalukStat,
  type UnsoldInventory,
} from "../api";

type Metric = "projects" | "sold" | "units";
type Granularity = "month" | "quarter";
type Split = "combined" | "byType";

function metricValue(
  row: { projects: number; total_units?: number; sell_through?: number | null },
  metric: Metric,
): number {
  if (metric === "sold") return row.sell_through === null || row.sell_through === undefined ? 0 : Math.round(row.sell_through * 100);
  if (metric === "units") return row.total_units ?? 0;
  return row.projects;
}

export default function MarketPage() {
  const [metric, setMetric] = useState<Metric>("sold");
  const [granularity, setGranularity] = useState<Granularity>("month");
  const [split, setSplit] = useState<Split>("combined");

  const districts = useApi<DistrictStat[]>("/districts");
  const taluks = useApi<TalukStat[]>("/locations/by-taluk");
  const unsold = useApi<UnsoldInventory>("/market/unsold");
  const pipeline = useApi<PipelineYear[]>("/market/pipeline");
  const trend = useApi<RegistrationTrend>("/market/registrations", {
    granularity,
    by_type: split === "byType",
  });
  const mix = useApi<ProjectMix>("/market/mix");
  const concentration = useApi<Concentration>("/market/concentration");

  if (districts.loading) return <Loader label="Loading market analytics…" />;
  if (districts.error) return <ErrorBox message={districts.error} />;

  const districtMap = (districts.data ?? []).map((d) => ({
    name: d.district ?? "Unknown",
    value: metricValue(d, metric),
  }));
  const talukMap = (taluks.data ?? []).map((t) => ({
    name: t.taluk,
    value: metricValue(t, metric),
  }));

  const unsoldByDistrict = [...(unsold.data?.by_district ?? [])].slice(0, 12);
  const unsoldByType = [...(unsold.data?.by_type ?? [])];

  const mixDistricts = mix.data?.districts ?? [];
  const mixTypes = mix.data?.types ?? [];
  const mixSeries = mixTypes.map((type) => ({
    name: type,
    type: "bar" as const,
    stack: "mix",
    emphasis: { focus: "series" as const },
    data: mixDistricts.map(
      (d) => mix.data?.data.find((x) => x.district === d && x.type === type)?.count ?? 0,
    ),
  }));

  const metricLabel = metric === "sold" ? "Share sold %" : metric === "units" ? "Units" : "Projects";

  return (
    <>
      <PageHeader
        eyebrow="Market"
        title="Supply, demand & registrations"
        subtitle="Where units are moving, what's unsold, and how the market is changing"
        right={
          <Segmented<Metric>
            label="Map metric"
            value={metric}
            onChange={setMetric}
            options={[
              { value: "projects", label: "Projects" },
              { value: "sold", label: "Share sold %" },
              { value: "units", label: "Units" },
            ]}
          />
        }
      />

      <Card title="Demand heatmap" subtitle={`District and taluk by ${metricLabel.toLowerCase()}`}>
        <div className="grid">
          <div>
            <KeralaMap data={districtMap} metric={metricLabel} height={420} />
          </div>
          <div>
            <KeralaTalukMap data={talukMap} height={420} />
          </div>
        </div>
      </Card>

      <div className="kpis">
        <Kpi icon="layers" tone="saffron" label="Unsold units" value={fmtInt(unsold.data?.unsold_units)} />
        <Kpi icon="home" tone="ocean" label="Units planned" value={fmtInt(unsold.data?.total_units)} />
        <Kpi icon="tag" tone="brand" label="Units sold" value={fmtInt(unsold.data?.sold_units)} />
        <Kpi icon="percent" tone="plum" label="Top-10 builders' share" value={fmtPct(concentration.data?.top10_share)} hint="of all units" />
        <Kpi icon="building" tone="slate" label="Single-project builders" value={fmtInt(concentration.data?.single_project_promoters)} hint={`of ${fmtInt(concentration.data?.promoters)} builders`} />
        <Kpi icon="layers" tone="slate" label="Units with no total" value={fmtInt(unsold.data?.undisclosed_projects)} hint="projects, not disclosed" />
      </div>

      <div className="grid">
        <Card title="Unsold inventory by district" subtitle="Planned − sold units">
          <EChart
            height={Math.max(280, unsoldByDistrict.length * 30)}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 120, right: 30, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: { type: "category", data: [...unsoldByDistrict].reverse().map((d) => d.district ?? "Unknown") },
              series: [
                {
                  type: "bar",
                  data: [...unsoldByDistrict].reverse().map((d) => d.unsold_units),
                  itemStyle: { color: "#c2410c", borderRadius: [0, 3, 3, 0] },
                },
              ],
            }}
          />
        </Card>

        <Card title="Unsold inventory by type" subtitle="Planned − sold units">
          <EChart
            height={Math.max(280, unsoldByType.length * 40)}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 210, right: 30, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: { type: "category", data: [...unsoldByType].reverse().map((d) => d.type ?? "Unknown") },
              series: [
                {
                  type: "bar",
                  data: [...unsoldByType].reverse().map((d) => d.unsold_units),
                  itemStyle: { color: "#24405f", borderRadius: [0, 3, 3, 0] },
                },
              ],
            }}
          />
        </Card>
      </div>

      <Card title="Supply pipeline" subtitle="Units in progress by declared completion year">
        <EChart
          height={320}
          option={{
            tooltip: {
              trigger: "axis",
              formatter: (params: any) => {
                const p = params[0];
                const row = (pipeline.data ?? [])[p.dataIndex];
                return `${p.name}<br/>Units: ${p.value}<br/>Projects: ${row?.projects ?? 0}`;
              },
            },
            grid: { left: 60, right: 20, top: 20, bottom: 30 },
            xAxis: { type: "category", data: (pipeline.data ?? []).map((d) => String(d.year)) },
            yAxis: { type: "value" },
            series: [
              {
                type: "bar",
                data: (pipeline.data ?? []).map((d) => d.units),
                itemStyle: { color: "#0d7a6f", borderRadius: [3, 3, 0, 0] },
              },
            ],
          }}
        />
      </Card>

      <Card
        title="Registration trend"
        subtitle="New registrations by certificate date"
        right={
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Segmented<Granularity>
              value={granularity}
              onChange={setGranularity}
              options={[
                { value: "month", label: "Month" },
                { value: "quarter", label: "Quarter" },
              ]}
            />
            <Segmented<Split>
              value={split}
              onChange={setSplit}
              options={[
                { value: "combined", label: "Combined" },
                { value: "byType", label: "By type" },
              ]}
            />
          </div>
        }
      >
        <EChart
          height={340}
          option={{
            tooltip: { trigger: "axis" },
            legend: { bottom: 0, type: "scroll" },
            grid: { left: 48, right: 20, top: 20, bottom: 46 },
            xAxis: { type: "category", data: trend.data?.periods ?? [] },
            yAxis: { type: "value" },
            series: (trend.data?.series ?? []).map((s) => ({
              name: s.name,
              type: "line",
              smooth: true,
              symbol: "none",
              lineStyle: { width: 2.5 },
              data: s.data,
            })),
          }}
        />
      </Card>

      <Card title="Project mix by district" subtitle="Registered projects by type">
        <EChart
          height={360}
          option={{
            tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
            legend: { bottom: 0, type: "scroll" },
            grid: { left: 48, right: 20, top: 20, bottom: 60 },
            xAxis: { type: "category", data: mixDistricts, axisLabel: { interval: 0, rotate: 30 } },
            yAxis: { type: "value" },
            series: mixSeries,
          }}
        />
      </Card>
    </>
  );
}
