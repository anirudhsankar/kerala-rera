import { Link, useParams } from "react-router-dom";
import { EChart } from "../components/EChart";
import { Card, ErrorBox, Kpi, Loader, fmtInt, fmtPct } from "../components/ui";
import { useApi, type DistrictDetail } from "../api";

export default function DistrictDetailPage() {
  const { district = "" } = useParams();
  const { data, error, loading } = useApi<DistrictDetail>(
    `/districts/${encodeURIComponent(district)}`,
  );

  if (loading) return <Loader />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return <ErrorBox message="District not found" />;

  const s = data.summary;

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">District</p>
          <h2>{data.district}</h2>
          <p className="muted small">
            <Link className="link" to="/districts">
              ← All districts
            </Link>
          </p>
        </div>
      </div>

      <div className="kpis">
        <Kpi icon="building" tone="brand" label="Projects" value={fmtInt(s.projects)} />
        <Kpi icon="home" tone="ocean" label="Units planned" value={fmtInt(s.total_units)} />
        <Kpi icon="tag" tone="saffron" label="Units sold" value={fmtInt(s.sold_units)} />
        <Kpi icon="percent" tone="plum" label="Share sold" value={fmtPct(s.sell_through)} />
        <Kpi icon="clock" tone="slate" label="Completed" value={fmtInt(s.completed)} />
        <Kpi icon="layers" tone="ocean" label="Ongoing" value={fmtInt(s.inprogress)} />
      </div>

      <div className="grid">
        <Card title="Project type mix">
          <EChart
            height={320}
            option={{
              tooltip: { trigger: "item" },
              legend: { bottom: 0, type: "scroll" },
              series: [
                {
                  type: "pie",
                  radius: ["42%", "70%"],
                  data: data.by_type.map((t) => ({ name: t.type ?? "Unknown", value: t.count })),
                  label: { formatter: "{b}: {c}" },
                },
              ],
            }}
          />
        </Card>

        <Card title="Taluks" subtitle="Tap a taluk to find its projects">
          <EChart
            height={320}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 150, right: 24, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: {
                type: "category",
                data: [...data.taluks].reverse().map((t) => t.taluk),
              },
              series: [
                {
                  type: "bar",
                  data: [...data.taluks].reverse().map((t) => t.count),
                  itemStyle: { color: "#7a5af8" },
                },
              ],
            }}
          />
          <div className="pills" style={{ marginTop: 14 }}>
            {data.taluks.map((t) => (
              <Link
                className="pill"
                key={t.taluk}
                to={`/find?district=${encodeURIComponent(data.district)}&taluk=${encodeURIComponent(t.taluk)}`}
              >
                <span className="dot" />
                {t.taluk} · {t.count}
              </Link>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Top builders in district" subtitle="By project count (canonicalised names)">
        <EChart
          height={Math.max(240, data.top_builders.length * 34)}
          option={{
            tooltip: { trigger: "axis" },
            grid: { left: 230, right: 30, top: 10, bottom: 20 },
            xAxis: { type: "value" },
            yAxis: {
              type: "category",
              data: [...data.top_builders].reverse().map((b) => b.name),
            },
            series: [
              {
                type: "bar",
                data: [...data.top_builders].reverse().map((b) => b.projects),
                itemStyle: { color: "#e08a1e" },
              },
            ],
          }}
        />
      </Card>
    </>
  );
}
