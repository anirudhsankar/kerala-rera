import type { ReactNode } from "react";

export const fmtInt = (n: number | null | undefined): string =>
  n === null || n === undefined ? "—" : n.toLocaleString("en-IN");

export const fmtPct = (x: number | null | undefined): string =>
  x === null || x === undefined ? "—" : `${(x * 100).toFixed(1)}%`;

export const fmtDate = (s: string | null | undefined): string =>
  s ? s.slice(0, 10) : "—";

export type IconName =
  | "building"
  | "home"
  | "tag"
  | "pin"
  | "percent"
  | "clock"
  | "layers"
  | "search"
  | "sun"
  | "moon"
  | "arrow";

export function Icon({ name, size = 22 }: { name: IconName; size?: number }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.9,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (name) {
    case "building":
      return (
        <svg {...common}>
          <path d="M3 21h18" />
          <path d="M5 21V4.5A1.5 1.5 0 0 1 6.5 3h7A1.5 1.5 0 0 1 15 4.5V21" />
          <path d="M15 21V9h3.5A1.5 1.5 0 0 1 20 10.5V21" />
          <path d="M8.5 7h2M8.5 11h2M8.5 15h2" />
        </svg>
      );
    case "home":
      return (
        <svg {...common}>
          <path d="M3 10.5 12 3l9 7.5" />
          <path d="M5 9.5V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9.5" />
          <path d="M9.5 21v-6h5v6" />
        </svg>
      );
    case "tag":
      return (
        <svg {...common}>
          <path d="M20.6 13.4 12.9 21a1.6 1.6 0 0 1-2.3 0L3 13.4V3h10.4l7.2 7.2a1.6 1.6 0 0 1 0 2.2Z" />
          <circle cx="7.8" cy="7.8" r="1.4" />
        </svg>
      );
    case "pin":
      return (
        <svg {...common}>
          <path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11Z" />
          <circle cx="12" cy="10" r="2.6" />
        </svg>
      );
    case "percent":
      return (
        <svg {...common}>
          <path d="M19 5 5 19" />
          <circle cx="7" cy="7" r="2.6" />
          <circle cx="17" cy="17" r="2.6" />
        </svg>
      );
    case "clock":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7.5V12l3 2" />
        </svg>
      );
    case "layers":
      return (
        <svg {...common}>
          <path d="m12 3 9 5-9 5-9-5 9-5Z" />
          <path d="m3 13 9 5 9-5" />
        </svg>
      );
    case "search":
      return (
        <svg {...common}>
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.2-3.2" />
        </svg>
      );
    case "sun":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      );
    case "moon":
      return (
        <svg {...common}>
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      );
    case "arrow":
      return (
        <svg {...common}>
          <path d="M5 12h14" />
          <path d="m13 6 6 6-6 6" />
        </svg>
      );
  }
  return null;
}

export function Hero({
  eyebrow,
  title,
  subtitle,
  stats,
  actions,
}: {
  eyebrow?: string;
  title: string;
  subtitle: string;
  stats: { label: string; value: ReactNode }[];
  actions?: ReactNode;
}) {
  return (
    <section className="hero">
      <div className="hero-inner">
        {eyebrow && (
          <p className="eyebrow" style={{ color: "rgba(255,255,255,.88)" }}>
            {eyebrow}
          </p>
        )}
        <h1>{title}</h1>
        <p className="lede">{subtitle}</p>
        <div className="hero-stats">
          {stats.map((s) => (
            <div className="hero-stat" key={s.label}>
              <b>{s.value}</b>
              <span>{s.label}</span>
            </div>
          ))}
        </div>
        {actions && <div className="hero-cta">{actions}</div>}
      </div>
    </section>
  );
}

export function Kpi({
  label,
  value,
  hint,
  icon,
  tone = "brand",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: IconName;
  tone?: "brand" | "ocean" | "saffron" | "plum" | "slate";
}) {
  return (
    <div className={`kpi tone-${tone}`}>
      {icon && (
        <div className={`kpi-icon ${tone === "brand" ? "" : tone}`}>
          <Icon name={icon} />
        </div>
      )}
      <div className="kpi-body">
        <div className="kpi-label">{label}</div>
        <div className="kpi-value">{value}</div>
        {hint && <div className="kpi-hint">{hint}</div>}
      </div>
    </div>
  );
}

export function Pill({
  children,
  tone = "brand",
}: {
  children: ReactNode;
  tone?: "brand" | "ocean" | "saffron";
}) {
  return (
    <span className={`pill ${tone === "brand" ? "" : tone}`}>
      <span className="dot" />
      {children}
    </span>
  );
}

export function Skeleton({
  height = 14,
  width = "100%",
  radius = 10,
}: {
  height?: number;
  width?: number | string;
  radius?: number;
}) {
  return <div className="skeleton" style={{ height, width, borderRadius: radius }} />;
}

export function Card({
  title,
  subtitle,
  children,
  right,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  right?: ReactNode;
}) {
  return (
    <section className="card">
      {(title || right) && (
        <header className="card-head">
          <div>
            {title && <h3>{title}</h3>}
            {subtitle && <p className="muted small">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}

export function Loader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="state">
      <div className="spinner" />
      {label}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return <div className="state error">Something went wrong: {message}</div>;
}

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render?: (row: T) => ReactNode;
}

export function Table<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
}) {
  if (!rows.length) return <div className="state muted">No rows to show.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.align === "right" ? "right" : ""}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className={onRowClick ? "clickable" : ""}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((col) => (
                <td key={col.key} className={col.align === "right" ? "right" : ""}>
                  {col.render ? col.render(row) : ((row as any)[col.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
