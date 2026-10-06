import { useEffect, useRef } from "react";
import * as echarts from "echarts";

const THEME_NAME = "rera";

let themeRegistered = false;
function ensureTheme() {
  if (themeRegistered) return;
  echarts.registerTheme(THEME_NAME, {
    color: ["#0d7a6f", "#0ea5e9", "#f59e0b", "#7c3aed", "#ef4444", "#14b8a6", "#64748b"],
    textStyle: {
      fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
      color: "#0f2a28",
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: "#dbe7e3" } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { color: "#5f7671" },
    },
    valueAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "#eef4f2" } },
      axisLabel: { color: "#5f7671" },
    },
    legend: { textStyle: { color: "#5f7671" }, icon: "roundRect" },
    tooltip: {
      backgroundColor: "rgba(15,42,40,0.92)",
      borderWidth: 0,
      textStyle: { color: "#ffffff" },
      extraCssText: "border-radius:10px;padding:8px 12px;",
    },
    bar: { itemStyle: { borderRadius: [6, 6, 0, 0] } },
    line: { smooth: true, symbolSize: 7, lineStyle: { width: 3 } },
    pie: { itemStyle: { borderColor: "#ffffff", borderWidth: 2 } },
    map: {
      itemStyle: { areaColor: "#e3f1ed", borderColor: "#ffffff" },
      label: { color: "#3c5b55" },
      emphasis: { itemStyle: { areaColor: "#f6c66b" } },
    },
  });
  themeRegistered = true;
}

export function EChart({
  option,
  height = 360,
}: {
  option: echarts.EChartsOption;
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    ensureTheme();
    chart.current = echarts.init(ref.current, THEME_NAME);
    const resize = () => chart.current?.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.current?.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    chart.current?.setOption(option, true);
  }, [option]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
