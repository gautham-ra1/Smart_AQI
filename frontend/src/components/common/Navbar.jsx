import { NavLink } from "react-router-dom";
import { Activity, Shield, User, HeartPulse, History, LogOut } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <div className="brand">
        <Activity size={20} color="#38bdf8" />
        <h1>VayuMesh</h1>
        <span className="brand-pill">Chikkamagaluru – Sringeri · v2.0</span>
      </div>

      <nav className="nav-links">
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          Live Fusion Map
        </NavLink>
        <NavLink to="/advisory" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          <HeartPulse size={14} /> Advisories
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          <History size={14} /> History & Tech
        </NavLink>
        <NavLink to="/citizen" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          <User size={14} /> Citizen / IoT Portal
        </NavLink>
        <NavLink to="/admin" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          <Shield size={14} /> Admin
        </NavLink>
      </nav>

      <div className="topbar-controls">
        {user ? (
          <>
            <span className="brand-pill">
              {user.full_name} ({user.role})
            </span>
            <button className="btn" onClick={logout}>
              <LogOut size={13} /> Logout
            </button>
          </>
        ) : (
          <NavLink to="/citizen" className="btn active" style={{ textDecoration: "none" }}>
            Sign In / Register
          </NavLink>
        )}
      </div>
    </header>
  );
}
