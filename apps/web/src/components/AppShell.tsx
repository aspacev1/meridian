import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

const NAV_ITEMS = [
  { to: "/dashboard", icon: "⬡", label: "Home" },
  { to: "/catalog", icon: "◫", label: "Catalog" },
  { to: "/tasks", icon: "◈", label: "Tasks" },
  { to: "/chat", icon: "◌", label: "Chat" },
  { to: "/settings", icon: "⚙", label: "Settings" },
];

export function AppShell() {
  const { me, currentOrgId, setCurrentOrgId, logout } = useAuth();
  const navigate = useNavigate();

  const currentMembership = me?.memberships.find((m) => m.org_id === currentOrgId);

  return (
    <div className="shell">
      <nav className="sb">
        <div className="sb-logo" onClick={() => navigate("/dashboard")}>
          M
        </div>
        <div className="sb-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `ni${isActive ? " active" : ""}`}
              title={item.label}
            >
              <div className="ni-icon">{item.icon}</div>
              <span className="ni-label">{item.label}</span>
            </NavLink>
          ))}
        </div>
        <div className="sb-bottom">
          <NavLink to="/executive" className="ni" title="Executive View" style={{ marginBottom: 8 }}>
            <div className="ni-icon">◉</div>
            <span className="ni-label">Executive</span>
          </NavLink>
          <div
            className="sb-av"
            title={me ? `${me.full_name} — sign out` : ""}
            onClick={logout}
          >
            {me?.avatar_initials || "?"}
          </div>
        </div>
      </nav>

      <div className="area">
        <div className="topbar">
          <div className="tb-breadcrumb">
            <span className="cur">{currentMembership?.org_name ?? "Meridian"}</span>
          </div>
          <div className="tb-right">
            {me && me.memberships.length > 1 && (
              <div className="org-switcher">
                <select
                  value={currentOrgId ?? ""}
                  onChange={(e) => setCurrentOrgId(e.target.value)}
                >
                  {me.memberships.map((m) => (
                    <option key={m.org_id} value={m.org_id}>
                      {m.org_name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
