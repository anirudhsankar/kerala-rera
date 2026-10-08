import { Link } from "react-router-dom";
import { EChart } from "../components/EChart";
import { Card, ErrorBox, Hero, Kpi, Loader, Pill, fmtInt, fmtPct } from "../components/ui";
import {
  useApi,
  type BuilderStat,
  type DistrictStat,
  type NewProjects,
  type Overview,
  type TimelineData,
} from "../api";

export default function OverviewPage() {
  const ov = useApi<Overview>("/overview");
  const tl = useApi<TimelineData>("/timeline", { granularity: "year" });
  const dist = useApi<DistrictStat[]>("/districts");
  const build = useApi<BuilderStat[]>("/builders", { limit: 6, sort: "projects" });
  const recent = useApi<NewProjects>("/projects/new", { months: 12, limit: 6 });

  if (ov.loading || tl.loading) return <Loader label="Loading the Kerala picture…" />;
  if (ov.error) return <ErrorBox message={ov.error} />;
  if (tl.error) return <ErrorBox message={tl.error} />;

  const o = ov.data!;
  const t = tl.data!;
  const topDistricts = [...(dist.data ?? [])].sort((a, b) => b.projects - a.projects).slice(0, 7);
  const maxProjects = Math.max(1, ...topDistricts.map((d) => d.projects));

  return (
    <>
      <Hero
        eyebrow="Kerala real estate · open data"
        title="Explore the homes and projects being built across Kerala"
        subtitle="Every RERA-registered project, organised by district, builder and status — free and open for everyone."
        stats={[
          { label: "Registered projects", value: fmtInt(o.total_projects) },
          { label: "Units planned", value: fmtInt(o.total_units) },
          { label: "Units sold", value: fmtInt(o.sold_units) },
          { label: "Share sold", value: fmtPct(o.sell_through) },
        ]}
        actions={
          <>
            <Link className="solid" to="/districts">Explore by district</Link>
            <Link className="ghost" to="/projects">Browse all projects</Link>
          </>
        }
      />

      <div className="pills" style={{ marginBottom: 20 }}>
        <Pill>14 districts covered</Pill>
        <Pill tone="ocean">{fmtInt(o.units_under_development)} units under development</Pill>
        <Pill tone="saffron">{fmtInt(o.declared_completion_date_passed)} past declared completion</Pill>
      </div>

      <div className="kpis">
        <Kpi icon="building" tone="brand" label="Registered projects" value={fmtInt(o.total_projects)} />
        <Kpi icon="home" tone="ocean" label="Units planned" value={fmtInt(o.total_units)} hint={`Across ${fmtInt(o.projects_with_units)} projects`} />
        <Kpi icon="tag" tone="saffron" label="Units sold" value={fmtInt(o.sold_units)} />
        <Kpi icon="percent" tone="plum" label="Share sold" value={fmtPct(o.sell_through)} hint="sold ÷ planned" />
        <Kpi icon="layers" tone="slate" label="Under development" value={fmtInt(o.units_under_development)} />
        <Kpi icon="clock" tone="ocean" label="Past declared completion" value={fmtInt(o.declared_completion_date_passed)} hint="a date comparison, not a delay" />
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
                    opacity: 0.25,
                    color: {
                      type: "linear", x: 0, y: 0, x2: 0, y2: 1,
                      colorStops: [
                        { offset: 0, color: "#14b8a6" },
                        { offset: 1, color: "rgba(20,184,166,0.04)" },
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
                      type: "linear", x: 0, y: 0, x2: 0, y2: 1,
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
        <Card
          title="Top districts"
          subtitle="Where development is concentrated"
          right={<Link className="link" to="/districts">View all →</Link>}
        >
          <div className="mini-list">
            {topDistricts.map((d, i) => (
              <Link className="mini-item" to={`/districts/${encodeURIComponent(d.district ?? "")}`} key={d.district ?? i}>
                <span className="mini-rank">{i + 1}</span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span className="mini-name">{d.district ?? "Unknown"}</span>
                  <span className="mini-bar">
                    <span style={{ width: `${(d.projects / maxProjects) * 100}%` }} />
                  </span>
                </span>
                <span className="mini-value">{fmtInt(d.projects)}</span>
              </Link>
            ))}
            {dist.loading && <div className="state muted">Loading…</div>}
          </div>
        </Card>

        <Card
          title="Most active builders"
          subtitle="By number of registered projects"
          right={<Link className="link" to="/builders">View all →</Link>}
        >
          <div className="mini-list">
            {(build.data ?? []).map((b, i) => (
              <Link className="mini-item" to={`/builders/${b.promoter_id}`} key={b.promoter_id}>
                <span className="mini-rank">{i + 1}</span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span className="mini-name">{b.name}</span>
                  <span className="mini-sub">
                    {fmtInt(b.total_units)} units · {b.districts} districts
                  </span>
                </span>
                <span className="mini-value">{fmtInt(b.projects)}</span>
              </Link>
            ))}
            {build.loading && <div className="state muted">Loading…</div>}
          </div>
        </Card>
      </div>

      <Card
        title="Newly registered"
        subtitle="Projects added to the register in the last 12 months"
        right={<Link className="link" to="/find">Find near you →</Link>}
      >
        <div className="mini-list">
          {(recent.data?.items ?? []).map((p, i) => (
            <Link
              className="mini-item"
              key={p.rera_registration_number}
              to={`/project?registration_number=${encodeURIComponent(p.rera_registration_number)}`}
            >
              <span className="mini-rank">{i + 1}</span>
              <span style={{ minWidth: 0, flex: 1 }}>
                <span className="mini-name">{p.project_name ?? "—"}</span>
                <span className="mini-sub">
                  {p.district ?? "—"}
                  {p.taluk ? ` · ${p.taluk}` : ""} · registered{" "}
                  {p.certificate_date ? p.certificate_date.slice(0, 10) : "—"}
                </span>
              </span>
              <span className="mini-value">{fmtInt(p.total_units)}</span>
            </Link>
          ))}
          {recent.loading && <div className="state muted">Loading…</div>}
          {!recent.loading && (recent.data?.items?.length ?? 0) === 0 && (
            <div className="state muted">No recent registrations found.</div>
          )}
        </div>
      </Card>

      <div className="provenance">
        <strong>In plain words.</strong> Figures come from the official K-RERA
        project register. “Share sold” is sold units ÷ planned units (plots
        without a unit count are left out). “Past declared completion” simply
        compares today’s date with the completion date a promoter declared — it
        is not a judgement that a project is delayed, and no builder is ever
        labelled as bad.
      </div>
    </>
  );
}
