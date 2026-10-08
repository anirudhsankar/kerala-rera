import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { useTheme } from "../theme";

const LIGHT = {
  color: ["#0d7a6f", "#0ea5e9", "#f59e0b", "#7c3aed", "#ef4444", "#14b8a6", "#64748b"],
  textStyle: { fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif', color: "#0f2a28" },
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
    backgroundColor: "rgba(15,42,40,0.94)",
    borderWidth: 0,
    textStyle: { color: "#ffffff" },
    extraCssText: "border-radius:12px;padding:9px 13px;box-shadow:0 8px 30px rgba(0,0,0,.25);",
  },
  bar: { itemStyle: { borderRadius: [6, 6, 0, 0] } },
  line: { smooth: true, symbolSize: 7, lineStyle: { width: 3 } },
  pie: { itemStyle: { borderColor: "#ffffff", borderWidth: 2 } },
  map: {
    itemStyle: { areaColor: "#e3f1ed", borderColor: "#ffffff" },
    label: { color: "#3c5b55" },
    emphasis: { itemStyle: { areaColor: "#f6c66b" } },
  },
};

const DARK = {
  color: ["#2dd4bf", "#38bdf8", "#fbbf24", "#a78bfa", "#f87171", "#34d399", "#94a3b8"],
  textStyle: { fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif', color: "#e7f2ee" },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#26403a" } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { color: "#93aaa3" },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: "#1d332d" } },
    axisLabel: { color: "#93aaa3" },
  },
  legend: { textStyle: { color: "#93aaa3" }, icon: "roundRect" },
  tooltip: {
    backgroundColor: "rgba(8,20,17,0.96)",
    borderWidth: 0,
    textStyle: { color: "#e7f2ee" },
    extraCssText: "border-radius:12px;padding:9px 13px;box-shadow:0 8px 30px rgba(0,0,0,.45);",
  },
  bar: { itemStyle: { borderRadius: [6, 6, 0, 0] } },
  line: { smooth: true, symbolSize: 7, lineStyle: { width: 3 } },
  pie: { itemStyle: { borderColor: "#101d18", borderWidth: 2 } },
  map: {
    itemStyle: { areaColor: "#16281f", borderColor: "#0b1512" },
    label: { color: "#9fb8b1" },
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
