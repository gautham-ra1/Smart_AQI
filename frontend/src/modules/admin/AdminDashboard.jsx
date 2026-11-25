import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, ShieldCheck, CloudDownload } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import {
  fetchAdminAuditLogs,
  fetchAdminOverview,
  fetchAdminUsers,
  fetchHeatmap,
  triggerFaultInjection,
  triggerRecompute,
  triggerSyncOfficial,
} from "../../services/api";

export default function AdminDashboard() {
  const { user, login, logout } = useAuth();
  const [overview, setOverview] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [sensors, setSensors] = useState([]);
  const [targetSensorId, setTargetSensorId] = useState("");
  const [biasPm25, setBiasPm25] = useState(150);
  const [recomputeMode, setRecomputeMode] = useState("kriging");
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const isAdmin = user?.role === "admin";

  const loadAdmin = async () => {
    try {
      const [ov, logs, us, hm] = await Promise.all([
        fetchAdminOverview(),
        fetchAdminAuditLogs(),
        fetchAdminUsers(),
        fetchHeatmap({ mode: "kriging", fusionMode: "hybrid", gridSize: 50 }),
      ]);
      setOverview(ov);
      setAuditLogs(logs);
      setUsers(us);
      setSensors((hm.sensors || []).filter((s) => s.sensor_type !== "official"));
    } catch (e) {
      if (e.response?.status === 401) {
        logout();
        setStatusMsg("Session expired (401). Please sign in as Admin again.");
      }
    }
  };

  useEffect(() => {
    if (isAdmin) loadAdmin();
  }, [isAdmin]);

  const handleAdminLogin = async () => {
    setBusy(true);
    try {
      await login("admin@vayumesh.in", "Admin@123");
      setStatusMsg("Authenticated as VayuMesh Admin.");
    } catch (e) {
      setStatusMsg(e.response?.data?.error?.message || e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleSyncOfficial = async () => {
    setBusy(true);
    try {
      const res = await triggerSyncOfficial();
      const src = res.stations?.[0]?.live_source || "live";
      const val = res.stations?.[0]?.pm25_raw ?? "—";
      setStatusMsg(`Synced official Kalyana Nagara KSPCB live (${val} µg/m³ via ${src}).`);
      await loadAdmin();
    } catch (e) {
      setStatusMsg(e.response?.data?.error?.message || e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleFault = async () => {
    setBusy(true);
    try {
      const res = await triggerFaultInjection(targetSensorId || null, Number(biasPm25), 10);
      setStatusMsg(
        `Injected +${biasPm25} µg/m³ on ${res.sensor_name}: trust decayed to ${res.final_trust} (${res.final_status}).`
      );
      await loadAdmin();
    } catch (e) {
      setStatusMsg(e.response?.data?.error?.message || e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleRecompute = async () => {
    setBusy(true);
    try {
      const res = await triggerRecompute(recomputeMode, null, 80);
      setStatusMsg(
        `Recomputed 80×80 ${res.mode_used.toUpperCase()} grid from immutable raw_readings in ${res.compute_ms} ms.`
      );
      await loadAdmin();
    } catch (e) {
      setStatusMsg(e.response?.data?.error?.message || e.message);
    } finally {
      setBusy(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className="page-container" style={{ maxWidth: 480 }}>
        <div className="card">
          <div className="card-title">Admin RBAC Control Center</div>
          <p style={{ fontSize: "0.82rem", color: "#94a3b8", marginBottom: 12 }}>
            Admin role is required for live CPCB syncing, synthetic fault injection, historical grid
            recomputation, and audit log inspection.
          </p>
          <button className="btn active" onClick={handleAdminLogin} disabled={busy}>
            <ShieldCheck size={14} /> One-Click Admin Demo Login (admin@vayumesh.in)
          </button>
          {statusMsg && <p style={{ marginTop: 10, fontSize: "0.78rem", color: "#fca5a5" }}>{statusMsg}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h2 style={{ marginBottom: 12 }}>Admin Control Center (RBAC Protected)</h2>
      {statusMsg && (
        <div className="card" style={{ marginBottom: 14, color: "#6ee7b7", fontSize: "0.82rem" }}>
          {statusMsg}
        </div>
      )}

      <div className="metric-row" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 16 }}>
        <div className="metric-box">
          <div className="metric-label">Registered Users</div>
          <div className="metric-value">{overview?.total_users ?? "—"}</div>
        </div>
        <div className="metric-box">
          <div className="metric-label">Total Sensors</div>
          <div className="metric-value">{overview?.total_sensors ?? "—"}</div>
        </div>
        <div className="metric-box">
          <div className="metric-label">Quarantined Nodes</div>
          <div className="metric-value" style={{ color: "#ef4444" }}>
            {overview?.quarantined_sensors ?? "—"}
          </div>
        </div>
        <div className="metric-box">
          <div className="metric-label">Immutable Raw Readings</div>
          <div className="metric-value">{overview?.immutable_raw_readings ?? "—"}</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-title">Live Demo Controls</div>
          <div className="form-group">
            <label>Target Virtual Sensor for Fault Injection</label>
            <select
              className="select-input"
              value={targetSensorId}
              onChange={(e) => setTargetSensorId(e.target.value)}
            >
              <option value="">Auto-pick highest-trust citizen/institutional node</option>
              {sensors.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} (trust {s.trust_weight})
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Persistent Bias (+µg/m³ over 10 ticks)</label>
            <input
              className="text-input"
              type="number"
              value={biasPm25}
              onChange={(e) => setBiasPm25(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="btn danger" onClick={handleFault} disabled={busy}>
              <AlertTriangle size={14} /> Inject Faulty Sensor
            </button>
            <button className="btn active" onClick={handleSyncOfficial} disabled={busy}>
              <CloudDownload size={14} /> Sync Official CPCB Live
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Recompute Grid from Immutable Logs (Constraint 3)</div>
          <p style={{ fontSize: "0.78rem", color: "#94a3b8", marginBottom: 10 }}>
            Replays raw telemetry directly from append-only <code>raw_readings</code> without mutating
            historical observations.
          </p>
          <div className="form-group">
            <label>Interpolation Engine</label>
            <select
              className="select-input"
              value={recomputeMode}
              onChange={(e) => setRecomputeMode(e.target.value)}
            >
              <option value="kriging">Trust-Aware Ordinary Kriging (80×80 + Uncertainty)</option>
              <option value="idw">Trust-Weighted IDW (80×80 Fast)</option>
            </select>
          </div>
          <button className="btn active" onClick={handleRecompute} disabled={busy}>
            <RefreshCw size={14} /> Recompute & Persist Grid
          </button>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Recent Admin Audit Logs</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Actor</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.slice(0, 12).map((a) => (
                <tr key={a.id}>
                  <td>{a.action}</td>
                  <td>{a.actor_email}</td>
                  <td>{new Date(a.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-title">Registered Accounts ({users.length})</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Cohort</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>{u.role}</td>
                  <td>{u.health_profile}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
