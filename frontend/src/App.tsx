import { useState } from "react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import Overview from "./pages/Overview";
import Districts from "./pages/Districts";
import DistrictDetail from "./pages/DistrictDetail";
import Builders from "./pages/Builders";
import BuilderDetail from "./pages/BuilderDetail";
import Projects from "./pages/Projects";
import ProjectDetail from "./pages/ProjectDetail";
import DataQuality from "./pages/DataQuality";
import Find from "./pages/Find";
import { Icon } from "./components/ui";
import { useTheme } from "./theme";

function BrandMark() {
  return (
    <span className="brand-mark">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5 9.5V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9.5" />
        <path d="M10 21v-5h4v5" />
      </svg>
    </span>
  );
}

function HeaderSearch() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  return (
    <form
      className="search"
      onSubmit={(e) => {
        e.preventDefault();
        navigate(q.trim() ? `/projects?q=${encodeURIComponent(q.trim())}` : "/projects");
      }}
      role="search"
    >
      <Icon name="search" size={16} />
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search projects, builders, districts…"
        aria-label="Search projects"
      />
    </form>
  );
}

export default function App() {
  const { theme, toggle } = useTheme();
  return (
    <>
      <header className="appbar">
        <div className="container appbar-inner">
          <NavLink to="/" className="brand">
            <BrandMark />
            <span className="brand-text">
              <b>Kerala RERA Intelligence</b>
              <span>Open real-estate insights</span>
            </span>
          </NavLink>
          <nav className="nav">
            <NavLink to="/" end>Overview</NavLink>
            <NavLink to="/find">Find projects</NavLink>
            <NavLink to="/districts">Districts</NavLink>
            <NavLink to="/builders">Builders</NavLink>
            <NavLink to="/projects">Projects</NavLink>
            <NavLink to="/data">About the data</NavLink>
          </nav>
          <HeaderSearch />
          <button
            className="theme-toggle"
            onClick={toggle}
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            aria-label="Toggle colour theme"
          >
            <Icon name={theme === "light" ? "moon" : "sun"} size={18} />
          </button>
        </div>
      </header>

      <main className="container page">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/find" element={<Find />} />
          <Route path="/districts" element={<Districts />} />
          <Route path="/districts/:district" element={<DistrictDetail />} />
          <Route path="/builders" element={<Builders />} />
          <Route path="/builders/:id" element={<BuilderDetail />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/project" element={<ProjectDetail />} />
          <Route path="/data" element={<DataQuality />} />
          <Route path="*" element={<div className="state">Page not found.</div>} />
        </Routes>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <span>
            A secondary, analytical dataset built from publicly available K-RERA
            information. Not an official K-RERA product.
          </span>
          <span>
            FastAPI + React · District boundaries: geohacker/india (GADM) ·
            <NavLink to="/data"> About the data</NavLink>
          </span>
        </div>
      </footer>
    </>
  );
}
