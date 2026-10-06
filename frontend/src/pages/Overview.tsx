import { EChart } from "../components/EChart";
import { Card, ErrorBox, Hero, Kpi, Loader, Pill, fmtInt, fmtPct } from "../components/ui";
import { useApi, type Overview, type TimelineData } from "../api";

export default function OverviewPage() {
  const ov = useApi<Overview>("/overview");
  const tl = useApi<TimelineData>("/timeline", { granularity: "year" });

  if (ov.loading || tl.loading) return <Loader label="Loading the Kerala picture…" />;
  if (ov.error) return <ErrorBox message={ov.error} />;
  if (tl.error) return <ErrorBox message={tl.error} />;

  const o = ov.data!;
  const t = tl.data!;
  const statusData = o.by_status.map((s) => ({ name: s.status ?? "Unknown", value: s.count }));

  return (
    <>
      <Hero
        eyebrow="Kerala real estate · open data"
        title="See what's being built across Kerala"
        subtitle="Every RERA-registered project in one place — explore by district, builder and status. Free, public and easy to understand."
        stats={[
          { label: "Registered projects", value: fmtInt(o.total_projects) },
          { label: "Units planned", value: fmtInt(o.total_units) },
          { label: "Units sold", value: fmtInt(o.sold_units) },
          { label: "Share sold", value: fmtPct(o.sell_through) },
        ]}
      />

      <div className="pills" style={{ marginBottom: 16 }}>
        <Pill>Districts covered: 14</Pill>
        <Pill>Past declared completion: {fmtInt(o.declared_completion_date_passed)} projects</Pill>
        <Pill>Still under development: {fmtInt(o.units_under_development)} units</Pill>
      </div>

      <div className="kpis">
        <Kpi icon="building" tone="brand" label="Registered projects" value={fmtInt(o.total_projects)} />
        <Kpi
          icon="home"
          tone="ocean"
          label="Units planned"
          value={fmtInt(o.total_units)}
          hint={`Across ${fmtInt(o.projects_with_units)} projects`}
        />
        <Kpi icon="tag" tone="saffron" label="Units sold" value={fmtInt(o.sold_units)} />
        <Kpi icon="percent" tone="plum" label="Share sold" value={fmtPct(o.sell_through)} hint="sold ÷ planned" />
        <Kpi icon="layers" tone="slate" label="Under development" value={fmtInt(o.units_under_development)} />
        <Kpi
          icon="clock"
          tone="ocean"
          label="Past declared completion"
          value={fmtInt(o.declared_completion_date_passed)}
          hint="factual date comparison"
        />
      </div>

      <div className="grid">
        <Card title="New registrations each year" subtitle="When projects joined the register">
          <EChart
            height={320}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 46, right: 20, top: 20, bottom: 34 },
              xAxis: { type: "category", data: t.registrations.map((d) => d.period) },
              yAxis: { type: "value" },
              series: [
                {
                  type: "line",
                  name: "Registrations",
                  areaStyle: {
                    opacity: 0.22,
                    color: {
                      type: "linear",
                      x: 0,
                      y: 0,
                      x2: 0,
                      y2: 1,
                      colorStops: [
                        { offset: 0, color: "#14b8a6" },
                        { offset: 1, color: "rgba(20,184,166,0.05)" },
                      ],
                    },
                  },
                  lineStyle: { color: "#0d7a6f" },
                  itemStyle: { color: "#0d7a6f" },
                  data: t.registrations.map((d) => d.count),
                },
              ],
            }}
          />
        </Card>

        <Card title="When projects say they'll finish" subtitle="Declared completion year">
          <EChart
            height={320}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 46, right: 20, top: 20, bottom: 34 },
              xAxis: { type: "category", data: t.declared_completions.map((d) => d.period) },
              yAxis: { type: "value" },
              series: [
                {
                  type: "bar",
                  name: "Projects",
                  data: t.declared_completions.map((d) => d.count),
                  itemStyle: {
                    borderRadius: [6, 6, 0, 0],
                    color: {
                      type: "linear",
                      x: 0,
                      y: 0,
                      x2: 0,
                      y2: 1,
                      colorStops: [
                        { offset: 0, color: "#38bdf8" },
                        { offset: 1, color: "#0ea5e9" },
                      ],
                    },
                  },
                },
              ],
            }}
          />
        </Card>
      </div>

      <div className="grid">
        <Card title="Are projects finished or ongoing?" subtitle="Status reported by K-RERA">
          <EChart
            height={300}
            option={{
              tooltip: { trigger: "item" },
              legend: { bottom: 0 },
              series: [
                {
                  type: "pie",
                  radius: ["48%", "74%"],
                  itemStyle: { borderRadius: 8 },
                  data: statusData,
                  label: { formatter: "{b}: {c}" },
                },
              ],
            }}
          />
        </Card>

        <Card title="What kind of projects?" subtitle="Count by declared type">
          <EChart
            height={300}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 210, right: 30, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: { type: "category", data: [...o.by_type].reverse().map((d) => d.type ?? "Unknown") },
              series: [
                {
                  type: "bar",
                  data: [...o.by_type].reverse().map((d) => d.count),
                  itemStyle: { borderRadius: [0, 6, 6, 0], color: "#7c3aed" },
                },
              ],
            }}
          />
        </Card>
      </div>

      <div className="provenance">
        <strong>Plain-language note.</strong> Figures come from the official
        K-RERA project register. “Share sold” is sold units ÷ planned units
        (plots without a unit count are excluded). “Past declared completion”
        simply compares today’s date with the completion date declared by the
        promoter — it is <em>not</em> a judgement that a project is delayed.
        This site never labels a project or a builder as “bad”.
      </div>
    </>
  );
}
