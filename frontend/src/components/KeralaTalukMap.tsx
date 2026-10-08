import { useEffect, useState } from "react";
import * as echarts from "echarts";
import { EChart } from "./EChart";

let mapPromise: Promise<void> | null = null;

function ensureMap(): Promise<void> {
  if (!mapPromise) {
    mapPromise = fetch("/kerala_taluks.geojson")
      .then((res) => res.json())
      .then((geo) => {
        echarts.registerMap("kerala-taluk", geo);
      });
  }
  return mapPromise;
}

export function KeralaTalukMap({
  data,
  height = 480,
}: {
  data: { name: string; value: number }[];
  height?: number;
}) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    ensureMap().then(() => setReady(true));
  }, []);

  const values = data.map((d) => d.value);
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: "item",
      formatter: (params: any) =>
        `${params.name}<br/>${params.value ?? "no data"} projects`,
    },
    visualMap: {
      min: 0,
      max: Math.max(1, ...values),
      left: 10,
      bottom: 10,
      text: ["More", "Fewer"],
      calculable: true,
      inRange: { color: ["#dff1ec", "#8cc9bd", "#0d7a6f"] },
    },
    series: [
      {
        type: "map",
        map: "kerala-taluk",
        roam: false,
        aspectScale: 1,
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 10 }, itemStyle: { areaColor: "#f6c66b" } },
        data,
      } as any,
    ],
  };

  if (!ready) return <div style={{ height }}>Loading map…</div>;
  return <EChart option={option} height={height} />;
}
