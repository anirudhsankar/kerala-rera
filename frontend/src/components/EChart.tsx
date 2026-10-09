import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { useTheme } from "../theme";

const LIGHT = {
  color: ["#0d7a6f", "#9ca3af", "#c2410c", "#24405f", "#7c3aed", "#0ea5e9", "#64748b"],
  textStyle: { fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif', color: "#0b1b22" },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#e6e8eb" } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { color: "#9ca3af" },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: "#f0f1f3" } },
    axisLabel: { color: "#9ca3af" },
  },
  legend: { textStyle: { color: "#6b7280" }, icon: "roundRect" },
  tooltip: {
    backgroundColor: "#ffffff",
    borderColor: "#e6e8eb",
    borderWidth: 1,
    textStyle: { color: "#0b1b22" },
    extraCssText: "border-radius:8px;box-shadow:0 8px 24px rgba(16,24,40,.12);padding:10px 12px;",
  },
  bar: { itemStyle: { borderRadius: [3, 3, 0, 0] } },
  line: { smooth: true, symbolSize: 6, lineStyle: { width: 2.5 } },
  pie: { itemStyle: { borderColor: "#ffffff", borderWidth: 2 } },
  map: {
    itemStyle: { areaColor: "#eef2f0", borderColor: "#ffffff" },
    label: { color: "#6b7280" },
    emphasis: { itemStyle: { areaColor: "#c7e6df" } },
  },
};

const DARK = {
  color: ["#2dd4bf", "#7c8a91", "#fb923c", "#7aa2d0", "#a78bfa", "#38bdf8", "#94a3b8"],
  textStyle: { fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif', color: "#e8eef1" },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#26343a" } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { color: "#74838a" },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: "#1c272c" } },
    axisLabel: { color: "#74838a" },
  },
  legend: { textStyle: { color: "#9aa7ad" }, icon: "roundRect" },
  tooltip: {
    backgroundColor: "#101a1e",
    borderColor: "#26343a",
    borderWidth: 1,
    textStyle: { color: "#e8eef1" },
    extraCssText: "border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.45);padding:10px 12px;",
  },
  bar: { itemStyle: { borderRadius: [3, 3, 0, 0] } },
  line: { smooth: true, symbolSize: 6, lineStyle: { width: 2.5 } },
  pie: { itemStyle: { borderColor: "#0b1418", borderWidth: 2 } },
  map: {
    itemStyle: { areaColor: "#16241f", borderColor: "#0b1418" },
    label: { color: "#9aa7ad" },
    emphasis: { itemStyle: { areaColor: "#0d7a6f" } },
  },
};

let registered = false;
function ensureThemes() {
  if (registered) return;
  echarts.registerTheme("rera-light", LIGHT);
  echarts.registerTheme("rera-dark", DARK);
  registered = true;
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
  const optionRef = useRef(option);
  optionRef.current = option;
  const { theme } = useTheme();

  useEffect(() => {
    if (!ref.current) return;
    ensureThemes();
    const instance = echarts.init(ref.current, `rera-${theme}`);
    chart.current = instance;
    instance.setOption(optionRef.current, true);
    const resize = () => chart.current?.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.current?.dispose();
      chart.current = null;
    };
  }, [theme]);

  useEffect(() => {
    chart.current?.setOption(option, true);
  }, [option]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
