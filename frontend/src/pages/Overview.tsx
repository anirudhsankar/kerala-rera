import { useState } from "react";
import { Link } from "react-router-dom";
import { EChart } from "../components/EChart";
import {
  Card,
  ErrorBox,
  Kpi,
  Loader,
  PageHeader,
  Pill,
  Segmented,
  fmtDate,
  fmtInt,
  fmtPct,
} from "../components/ui";
import {
  useApi,
  type BaselineInfo,
  type BuilderStat,
  type DistrictStat,
  type NewProjects,
  type Overview,
  type TimelineData,
} from "../api";

type Trend = "registrations" | "completions";

export default function OverviewPage() {
  const ov = useApi<Overview>("/overview");
  const tl = useApi<TimelineData>("/timeline", { granularity: "year" });
  const dist = useApi<DistrictStat[]>("/districts");
  const build = useApi<BuilderStat[]>("/builders", { limit: 6, sort: "projects" });
  const recent = useApi<NewProjects>("/projects/new", { months: 12, limit: 6 });
  const baseline = useApi<BaselineInfo | null>("/baseline");
  const [trend, setTrend] = useState<Trend>("registrations");

  if (ov.loading || tl.loading) return <Loader label="Loading the Kerala picture…" />;
  if (ov.error) return <ErrorBox message={ov.error} />;
  if (tl.error) return <ErrorBox message={tl.error} />;

  const o = ov.data!;
  const t = tl.data!;
  const topDistricts = [...(dist.data ?? [])].sort((a, b) => b.projects - a.projects).slice(0, 7);
  const maxProjects = Math.max(1, ...topDistricts.map((d) => d.projects));
  const statusPills = o.by_status.slice(0, 4);

  const trendData = trend === "registrations" ? t.registrations : t.declared_completions;
  const trendLabel = trend === "registrations" ? "New registrations" : "Declared completions";

  const completions = t.declared_completions;
  const peakIndex = completions.reduce((best, d, i) => (d.count > completions[best].count ? i : best), 0);
  const peak = completions[peakIndex];

  return (
    <>
      <PageHeader
        eyebrow="System overview"
        title="Kerala real-estate overview"
        subtitle={[
          `${fmtInt(o.total_projects)} registered projects`,
          `${fmtInt(o.total_units)} units planned`,
          "14 districts",
          baseline.data?.baseline_at ? `baseline ${fmtDate(baseline.data.baseline_at)}` : null,
        ]
          .filter(Boolean)
          .join(" · ")}
        right={
          <Segmented<Trend>
            label="Trend"
            value={trend}
            onChange={setTrend}
            options={[
              { value: "registrations", label: "Registrations" },
              { value: "completions", label: "Completions" },
            ]}
          />
        }
      />

      {statusPills.length > 0 && (
        <div className="pills" style={{ marginBottom: 20 }}>
          {statusPills.map((s) => (
            <Pill key={s.status ?? "unknown"} tone={s.status?.toLowerCase().includes("complete") ? "brand" : "saffron"}>
              {s.status ?? "Unknown"}: {fmtInt(s.count)}
            </Pill>
          ))}
        </div>
      )}

      <div className="kpis">
        <Kpi icon="building" tone="slate" label="Registered projects" value={fmtInt(o.total_projects)} />
        <Kpi
          icon="home"
          tone="saffron"
          label="Units planned"
          value={fmtInt(o.total_units)}
          hint={`Across ${fmtInt(o.projects_with_units)} projects`}
        />
        <Kpi icon="tag" tone="brand" label="Units sold" value={fmtInt(o.sold_units)} />
        <Kpi icon="percent" tone="saffron" label="Share sold" value={fmtPct(o.sell_through)} hint="sold ÷ planned" />
        <Kpi icon="layers" tone="slate" label="Under development" value={fmtInt(o.units_under_development)} />
        <Kpi
          icon="clock"
          tone="ocean"
          label="Past declared completion"
          value={fmtInt(o.declared_completion_date_passed)}
          hint="a date comparison, not a delay"
        />
      </div>

      <div className="grid">
        <Card title={`${trendLabel} per year`} subtitle="By certificate / declared completion date">
          <EChart
            height={330}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 48, right: 20, top: 20, bottom: 34 },
              xAxis: { type: "category", data: trendData.map((d) => d.period) },
              yAxis: { type: "value" },
              series: [
                {
                  type: "line",
                  name: trendLabel,
                  smooth: true,
                  symbol: "circle",
                  symbolSize: 6,
                  lineStyle: { width: 2.5, color: "#0d7a6f" },
                  itemStyle: { color: "#0d7a6f" },
                  areaStyle: {
                    opacity: 0.14,
                    color: {
                      type: "linear", x: 0, y: 0, x2: 0, y2: 1,
                      colorStops: [
                        { offset: 0, color: "#0d7a6f" },
                        { offset: 1, color: "rgba(13,122,111,0)" },
                      ],
                    },
                  },
                  data: trendData.map((d) => d.count),
                },
              ],
            }}
          />
        </Card>

        <Card title="Declared completion pipeline" subtitle="Projects by the year they say they'll finish">
          <EChart
            height={330}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 48, right: 20, top: 20, bottom: 34 },
              xAxis: { type: "category", data: completions.map((d) => d.period), boundaryGap: false },
              yAxis: { type: "value" },
              series: [
                {
                  type: "line",
                  name: "Projects",
                  smooth: true,
                  symbol: "none",
                  lineStyle: { width: 2.5, color: "#24405f" },
                  itemStyle: { color: "#24405f" },
                  markArea: peak
                    ? {
                        silent: true,
                        itemStyle: { color: "rgba(13,122,111,0.10)" },
                        data: [[{ xAxis: peak.period }, { xAxis: completions[peakIndex + 1]?.period ?? peak.period }]],
                      }
                    : undefined,
                  data: completions.map((d) => d.count),
                },
              ],
            }}
          />
        </Card>
      </div>

      <div className="grid thirds">
        <Card title="Top districts" subtitle="By project count" right={<Link className="link" to="/districts">All →</Link>}>
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

        <Card title="Most active builders" subtitle="By project count" right={<Link className="link" to="/builders">All →</Link>}>
          <div className="mini-list">
            {(build.data ?? []).map((b, i) => (
              <Link className="mini-item" to={`/builders/${b.promoter_id}`} key={b.promoter_id}>
                <span className="mini-rank">{i + 1}</span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span className="mini-name">{b.name}</span>
                  <span className="mini-sub">{fmtInt(b.total_units)} units · {b.districts} districts</span>
                </span>
                <span className="mini-value">{fmtInt(b.projects)}</span>
              </Link>
            ))}
            {build.loading && <div className="state muted">Loading…</div>}
          </div>
        </Card>

        <Card title="Newly registered" subtitle="Last 12 months" right={<Link className="link" to="/find">Find near you →</Link>}>
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
                    {p.taluk ? ` · ${p.taluk}` : ""}
                  </span>
                </span>
                <span className="mini-value">{fmtDate(p.certificate_date)}</span>
              </Link>
            ))}
            {recent.loading && <div className="state muted">Loading…</div>}
          </div>
        </Card>
      </div>

      <div className="provenance">
        <strong>In plain words.</strong> Figures come from the official K-RERA project
        register. “Share sold” is sold units ÷ planned units (plots without a unit
        count are left out). “Past declared completion” simply compares today’s date
        with the completion date a promoter declared — it is not a judgement that a
        project is delayed, and no builder is ever labelled as bad.
      </div>
    </>
  );
}
