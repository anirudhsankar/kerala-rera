import { EChart } from "../components/EChart";
import { Card, ErrorBox, Kpi, Loader, Table, fmtInt, type Column } from "../components/ui";
import { useApi, type BaselineInfo, type DQSummary, type RunInfo } from "../api";

export default function DataQualityPage() {
  const dq = useApi<DQSummary>("/data-quality/summary");
  const runs = useApi<RunInfo[]>("/runs", { limit: 20 });
  const baseline = useApi<BaselineInfo | null>("/baseline");

  if (dq.loading || runs.loading) return <Loader />;
  if (dq.error) return <ErrorBox message={dq.error} />;

  const d = dq.data!;
  const severity = d.by_severity;
  const types = [...(d.by_type ?? [])].slice(0, 12).reverse();

  const runColumns: Column<RunInfo>[] = [
    { key: "id", header: "#", align: "right", render: (r) => r.id },
    { key: "status", header: "Status", render: (r) => r.status },
    { key: "records_found", header: "Found", align: "right", render: (r) => fmtInt(r.records_found) },
    { key: "inserted", header: "New", align: "right", render: (r) => fmtInt(r.inserted) },
    { key: "updated", header: "Changed", align: "right", render: (r) => fmtInt(r.updated) },
    { key: "unchanged", header: "Unchanged", align: "right", render: (r) => fmtInt(r.unchanged) },
    { key: "failed", header: "Failed", align: "right", render: (r) => fmtInt(r.failed) },
    { key: "parser_version", header: "Parser", render: (r) => r.parser_version },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <p className="eyebrow">Transparency</p>
          <h2>About the data</h2>
          <p className="muted small">Where it comes from, and how it is checked.</p>
        </div>
      </div>

      <div className="kpis">
        <Kpi icon="layers" tone="brand" label="Quality checks" value={fmtInt(d.total)} />
        <Kpi icon="clock" tone="slate" label="Errors" value={fmtInt(severity.ERROR ?? 0)} />
        <Kpi icon="percent" tone="saffron" label="Warnings" value={fmtInt(severity.WARNING ?? 0)} />
        <Kpi icon="tag" tone="ocean" label="Notes" value={fmtInt(severity.INFO ?? 0)} />
      </div>

      <div className="grid">
        <Card title="Findings by type" subtitle="Top rules">
          <EChart
            height={Math.max(280, types.length * 30)}
            option={{
              tooltip: { trigger: "axis" },
              grid: { left: 220, right: 30, top: 10, bottom: 20 },
              xAxis: { type: "value" },
              yAxis: { type: "category", data: types.map((t) => t.issue_type) },
              series: [
                {
                  type: "bar",
                  data: types.map((t) => t.count),
                  itemStyle: { color: "#b45309" },
                },
              ],
            }}
          />
        </Card>

        <Card title="Baseline" subtitle="First full ingestion checkpoint">
          {baseline.data ? (
            <dl className="fields">
              <dt>Baseline date</dt>
              <dd>{baseline.data.baseline_at?.slice(0, 19).replace("T", " ")}</dd>
              <dt>Record count</dt>
              <dd>{fmtInt(baseline.data.record_count)}</dd>
              <dt>Parser version</dt>
              <dd>{baseline.data.parser_version}</dd>
              <dt>Source</dt>
              <dd>{baseline.data.source}</dd>
              <dt>Source checksum</dt>
              <dd style={{ wordBreak: "break-all" }}>{baseline.data.source_checksum}</dd>
            </dl>
          ) : (
            <div className="state muted">No baseline recorded.</div>
          )}
        </Card>
      </div>

      <Card title="Ingestion runs">
        <Table columns={runColumns} rows={runs.data ?? []} rowKey={(r) => r.id} />
      </Card>

      <div className="provenance">
        <strong>Where this data comes from.</strong> It is built from official
        K-RERA project-register exports (downloaded by a person through the
        public website). It is an independent, analytical copy — not an official
        K-RERA product. “Past declared completion” is just a date comparison and
        is not a statement that a project is delayed, and no builder is labelled
        as bad. Some projects (mostly plots) do not report a unit count. District
        boundaries come from the geohacker/india (GADM) dataset. We cannot
        confirm that any single export is the complete national register.
      </div>
    </>
  );
}
