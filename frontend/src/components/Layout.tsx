// App shell: persistent sidebar nav + routed content area.
// Mirrors the Streamlit sidebar ("Submit Claim" / "Review Claims" / "Eval").

import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/", label: "Submit Claim", end: true },
  { to: "/review", label: "Review Claims", end: false },
  { to: "/eval", label: "Eval (12 cases)", end: false },
];

export default function Layout() {
  return (
    <div className="pc-shell">
      <aside className="pc-sidebar">
        <div className="pc-brand">🏥 Plum Claims</div>
        <div className="pc-brand-sub">AI-powered medical claims processing</div>
        <nav className="pc-nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="pc-sidebar-foot">
          Plum Health Insurance
          <br />
          <span className="pc-mono">PLUM_GHI_2024</span>
        </div>
      </aside>
      <main className="pc-main">
        <div className="pc-main-inner">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
