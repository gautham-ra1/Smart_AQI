import { useEffect, useState, useCallback } from "react";
import { io } from "socket.io-client";
import {
  Activity,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
  Sliders,
  Zap,
} from "lucide-react";
import AQIMap from "./components/map/AQIMap";
import AdvisoryCard from "./components/advisory/AdvisoryCard";
import SensorTrustChart from "./components/charts/SensorTrustChart";
import {
  API_BASE_URL,
  fetchAdvisory,
  fetchHeatmap,
  fetchSensorTrustHistory,
  loginAccount,
  triggerFaultInjection,
  triggerRecompute,
} from "./services/api";
import { trustColor } from "./utils/aqiColors";

export default function App() {
  const [mode, setMode] = useState("kriging");
  const [showUncertainty, setShowUncertainty] = useState(true);
  const [profile, setProfile] = useState("asthma");
  const [heatmap, setHeatmap] = useState(null);
  const [advisory, setAdvisory] = useState(null);
  const [selectedSensor, setSelectedSensor] = useState(null);
  const [trustData, setTrustData] = useState(null);
  const [adminLoggedIn, setAdminLoggedIn] = useState(
    Boolean(localStorage.getItem("vayumesh_token"))
  );
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState("Connected to Chikkamagaluru live fusion engine");

  const loadData = useCallback(async () => {
    try {
      const hm = await fetchHeatmap(mode, "chikkamagaluru");
      setHeatmap(hm);
      const adv = await fetchAdvisory(profile, 13.3161, 75.772);
      setAdvisory(adv);
    } catch (err) {
      setStatusMsg(`Backend unreachable (${err.message})`);
    }
  }, [mode, profile]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Real-time Socket.io updates from Virtual IoT Devices & Admin Controls (debounced)
  useEffect(() => {
    const socket = io(API_BASE_URL, { transports: ["websocket", "polling"] });
    let refreshTimer = null;

    socket.on("connect", () => {
      socket.emit("join_city", { city: "chikkamagaluru" });
    });
    socket.on("heatmap_update", (data) => {
      setHeatmap(data);
      setStatusMsg(`Live grid updated (${data.mode_used.toUpperCase()} · ${data.compute_ms} ms)`);
    });
    socket.on("sensor_trust_update", (ev) => {
      setStatusMsg(
        `IoT packet: ${ev.sensor_name} | corr=${ev.pm25_corrected} µg/m³ | trust=${ev.new_trust}`
      );
      if (!refreshTimer) {
        refreshTimer = setTimeout(() => {
          refreshTimer = null;
          loadData();
        }, 1800);
      }
    });
    return () => {
      if (refreshTimer) clearTimeout(refreshTimer);
      socket.disconnect();
    };
  }, [loadData]);

  const handleSelectSensor = async (sensor) => {
    setSelectedSensor(sensor);
    try {
      const history = await fetchSensorTrustHistory(sensor.id);
      setTrustData(history);
    } catch {
      setTrustData(null);
    }
  };

  const handleAdminDemoLogin = async () => {
    setBusy(true);
    try {
      await loginAccount("admin@vayumesh.in", "Admin@123");
      setAdminLoggedIn(true);
      setStatusMsg("Signed in as Admin (RBAC unlocked for Fault Injection & Recompute)");
    } catch (e) {
      setStatusMsg(`Admin login failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleInjectFault = async () => {
    setBusy(true);
    try {
      const res = await triggerFaultInjection(
        selectedSensor && selectedSensor.sensor_type !== "official" ? selectedSensor.id : null,
        150,
        10
      );
      setStatusMsg(
        `Fault injected on ${res.sensor_name}: trust decayed to ${res.final_trust} (${res.final_status})`
      );
      await loadData();
      const history = await fetchSensorTrustHistory(res.sensor_id);
      setTrustData(history);
    } catch (e) {
      setStatusMsg(`Fault injection failed (sign in as Admin first): ${e.response?.data?.error?.message || e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleRecompute = async () => {
    setBusy(true);
    try {
      const grid = await triggerRecompute(mode);
      setHeatmap(grid);
      setStatusMsg(
        `Recomputed from immutable raw_readings (${grid.mode_used.toUpperCase()} in ${grid.compute_ms} ms)`
      );
    } catch (e) {
      setStatusMsg(`Recompute failed: ${e.response?.data?.error?.message || e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Activity size={20} color="#38bdf8" />
          <h1>VayuMesh</h1>
          <span className="brand-pill">Chikkamagaluru Pilot · Three-Tier Adaptive Fusion</span>
        </div>

        <div className="topbar-controls">
          <button
            className={`btn ${mode === "idw" ? "active" : ""}`}
            onClick={() => setMode("idw")}
          >
            <Zap size={14} /> Fast TW-IDW
          </button>
          <button
            className={`btn ${mode === "kriging" ? "active" : ""}`}
            onClick={() => setMode("kriging")}
          >
            <Sliders size={14} /> Precision Kriging
          </button>
          <button
            className={`btn ${showUncertainty ? "active" : ""}`}
            onClick={() => setShowUncertainty((v) => !v)}
          >
            Uncertainty Opacity
          </button>
          {!adminLoggedIn ? (
            <button className="btn active" onClick={handleAdminDemoLogin} disabled={busy}>
              <ShieldCheck size={14} /> Admin Demo Login
            </button>
          ) : (
            <>
              <button className="btn danger" onClick={handleInjectFault} disabled={busy}>
                <AlertTriangle size={14} /> Inject Fault (+150 µg/m³)
              </button>
              <button className="btn" onClick={handleRecompute} disabled={busy}>
                <RefreshCw size={14} /> Recompute from Logs
              </button>
            </>
          )}
        </div>
      </header>

      <main className="main-grid">
        <AQIMap
          heatmap={heatmap}
          showUncertainty={showUncertainty}
          selectedSensorId={selectedSensor?.id}
          onSelectSensor={handleSelectSensor}
        />

        <aside className="sidebar">
          <div className="card">
            <div className="card-title">
              <span>Live Telemetry Summary</span>
              <span style={{ color: "#38bdf8", fontSize: "0.7rem" }}>
                {heatmap?.cams_prior?.source || "Open-Meteo CAMS"}
              </span>
            </div>
            <div className="metric-row">
              <div className="metric-box">
                <div className="metric-label">Mean PM2.5</div>
                <div className="metric-value">{heatmap?.summary?.mean_pm25 ?? "—"} µg/m³</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Active Nodes</div>
                <div className="metric-value">{heatmap?.active_sensor_count ?? 0}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Grid Compute</div>
                <div className="metric-value">{heatmap?.compute_ms ?? "—"} ms</div>
              </div>
            </div>
            <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: 8 }}>{statusMsg}</div>
          </div>

          <AdvisoryCard
            advisory={advisory}
            profile={profile}
            onProfileChange={setProfile}
          />

          <div className="card">
            <div className="card-title">
              <span>EWMA Trust Trajectory</span>
              <span style={{ fontSize: "0.68rem", color: "#94a3b8" }}>α = 0.25 · floor 0.05</span>
            </div>
            <SensorTrustChart trustData={trustData} />
          </div>

          <div className="card">
            <div className="card-title">
              <span>Chikkamagaluru Sensor Fleet</span>
              <span style={{ fontSize: "0.7rem", color: "#94a3b8" }}>
                {heatmap?.sensors?.length || 0} nodes
              </span>
            </div>
            <div className="sensor-list">
              {(heatmap?.sensors || []).map((s) => (
                <div
                  key={s.id}
                  className={`sensor-item ${selectedSensor?.id === s.id ? "selected" : ""}`}
                  onClick={() => handleSelectSensor(s)}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>{s.name}</div>
                    <div style={{ fontSize: "0.68rem", color: "#94a3b8" }}>
                      {s.tier_used} · raw {s.pm25_raw} → {s.pm25_corrected} µg/m³ (RH {s.rh_pct}%)
                    </div>
                  </div>
                  <span
                    className="badge"
                    style={{
                      background: trustColor(s.trust_weight),
                      color: "#ffffff",
                    }}
                  >
                    {s.trust_weight.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
