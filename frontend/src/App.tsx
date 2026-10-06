import { NavLink, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview";
import Districts from "./pages/Districts";
import DistrictDetail from "./pages/DistrictDetail";
import Builders from "./pages/Builders";
import BuilderDetail from "./pages/BuilderDetail";
import Projects from "./pages/Projects";
import ProjectDetail from "./pages/ProjectDetail";
import DataQuality from "./pages/DataQuality";

function BrandMark() {
  return (
    <span className="brand-mark">
      <svg
        width="21"
        height="21"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5 9.5V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9.5" />
        <path d="M10 21v-5h4v5" />
      </svg>
    </span>
  );
}

export default function App() {
  return (
    <>
      <header className="topbar">
        <div className="container topbar-inner">
          <NavLink to="/" className="brand">
            <BrandMark />
            <span className="brand-text">
              <b>Kerala RERA Intelligence</b>
              <span>Public real-estate insights</span>
            </span>
          </NavLink>
          <nav className="nav">
            <NavLink to="/" end>
              Overview
            </NavLink>
            <NavLink to="/districts">Districts</NavLink>
            <NavLink to="/builders">Builders</NavLink>
            <NavLink to="/projects">Explore projects</NavLink>
            <NavLink to="/data">About the data</NavLink>
          </nav>
        </div>
      </header>

      <main className="container page">
        <Routes>
          <Route path="/" element={<Overview />} />
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
            Built with FastAPI + React. District boundaries: geohacker/india (GADM).
          </span>
        </div>
      </footer>
    </>
  );
}
