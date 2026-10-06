import { useEffect, useState } from "react";
import * as echarts from "echarts";
import { EChart } from "./EChart";

let mapPromise: Promise<void> | null = null;

function ensureMap(): Promise<void> {
  if (!mapPromise) {
    mapPromise = fetch("/kerala_districts.geojson")
      .then((res) => res.json())
      .then((geo) => {
        echarts.registerMap("kerala", geo);
      });
  }
  return mapPromise;
}

export function KeralaMap({
  data,
  height = 480,
  metric = "projects",
}: {
  data: { name: string; value: number }[];
  height?: number;
  metric?: string;
}) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    ensureMap().then(() => setReady(true));
  }, []);

  const values = data.map((d) => d.value);
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: "item",
      formatter: (params: any) => `${params.name}<br/>${metric}: ${params.value ?? 0}`,
    },
    visualMap: {
      min: 0,
      max: Math.max(1, ...values),
      left: 10,
      bottom: 10,
      text: ["High", "Low"],
      calculable: true,
      inRange: { color: ["#e8f1fb", "#9dc3f0", "#1f6feb"] },
    },
    series: [
      {
        type: "map",
        map: "kerala",
        roam: false,
        aspectScale: 1,
        label: { show: true, fontSize: 9 },
        emphasis: { label: { show: true }, itemStyle: { areaColor: "#f6b73c" } },
        data,
      } as any,
    ],
  };

  if (!ready) return <div style={{ height }}>Loading map…</div>;
  return <EChart option={option} height={height} />;
}
