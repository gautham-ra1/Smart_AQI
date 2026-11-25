import { useEffect, useState, useCallback, useRef } from "react";
import { io } from "socket.io-client";
import { AlertTriangle, Layers, MapPin, Satellite, Sliders, Zap } from "lucide-react";
import AQIMap from "../../components/map/AQIMap";
import AdvisoryCard from "../../components/advisory/AdvisoryCard";
import SensorTrustChart from "../../components/charts/SensorTrustChart";
import { useAuth } from "../../context/AuthContext";
import {
  API_BASE_URL,
  fetchAdvisory,
  fetchHeatmap,
  fetchSensorTrustHistory,
  triggerFaultInjection,
} from "../../services/api";
import { trustColor } from "../../utils/aqiColors";

export default function PublicHeatmap() {
  const { user, login } = useAuth();
  const [mode, setMode] = useState("kriging");
  const [fusionMode, setFusionMode] = useState("hybrid");
  const [gridSize, setGridSize] = useState(80);
  const [showUncertainty, setShowUncertainty] = useState(true);
  const [overlayOpacity, setOverlayOpacity] = useState(0.42);
  const [tileStyle, setTileStyle] = useState("street");
  const [flyTarget, setFlyTarget] = useState(null);
  const [profile, setProfile] = useState("asthma");
  const [heatmap, setHeatmap] = useState(null);
  const [advisory, setAdvisory] = useState(null);
  const [selectedSensor, setSelectedSensor] = useState(null);
  const [trustData, setTrustData] = useState(null);
  const [injecting, setInjecting] = useState(false);
  const [statusMsg, setStatusMsg] = useState("Connected to Chikkamagaluru–Sringeri fusion engine");
  const selectedSensorIdRef = useRef(null);

  const loadTrustHistory = useCallback(async (sensorId) => {
    if (!sensorId) return;
    try {
      const history = await fetchSensorTrustHistory(sensorId);
      setTrustData(history);
    } catch {
      // Ignore transient fetch errors
    }
  }, []);

  const loadData = useCallback(async () => {
    try {
      const hm = await fetchHeatmap({ mode, fusionMode, gridSize, city: "chikkamagaluru" });
      setHeatmap(hm);

      // Auto-select first non-official sensor so EWMA Trust Graph is immediately populated
      if (!selectedSensorIdRef.current && hm.sensors?.length) {
        const defaultNode =
          hm.sensors.find((s) => s.sensor_type !== "official") || hm.sensors[0];
        selectedSensorIdRef.current = defaultNode.id;
        setSelectedSensor(defaultNode);
        loadTrustHistory(defaultNode.id);
      } else if (selectedSensorIdRef.current) {
        const updated = hm.sensors?.find((s) => s.id === selectedSensorIdRef.current);
        if (updated) setSelectedSensor(updated);
        loadTrustHistory(selectedSensorIdRef.current);
      }

      const adv = await fetchAdvisory(profile, 13.3161, 75.772);
      setAdvisory(adv);
    } catch (err) {
      setStatusMsg(`Backend unreachable (${err.message})`);
    }
  }, [mode, fusionMode, gridSize, profile, loadTrustHistory]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const socket = io(API_BASE_URL, { transports: ["websocket", "polling"] });
    let refreshTimer = null;

    socket.on("connect", () => {
      socket.emit("join_city", { city: "chikkamagaluru" });
    });
    socket.on("heatmap_update", (data) => {
      setHeatmap(data);
      if (selectedSensorIdRef.current) {
        loadTrustHistory(selectedSensorIdRef.current);
      }
      setStatusMsg(`Live grid updated (${data.mode_used.toUpperCase()} · ${data.compute_ms} ms)`);
    });
    socket.on("sensor_trust_update", (ev) => {
      setStatusMsg(
        `Live IoT: ${ev.sensor_name} | corr=${ev.pm25_corrected} µg/m³ | trust=${ev.new_trust} [${ev.tier_used}]`
      );
      if (ev.sensor_id === selectedSensorIdRef.current) {
        loadTrustHistory(ev.sensor_id);
      }
      if (!refreshTimer) {
        refreshTimer = setTimeout(() => {
          refreshTimer = null;
          loadData();
        }, 2000);
      }
    });
    return () => {
      if (refreshTimer) clearTimeout(refreshTimer);
      socket.disconnect();
    };
  }, [loadData, loadTrustHistory]);

  const handleSelectSensor = async (sensor) => {
    selectedSensorIdRef.current = sensor.id;
    setSelectedSensor(sensor);
    setFlyTarget({ lat: sensor.lat, lon: sensor.lon, zoom: 13, _ts: Date.now() });
    await loadTrustHistory(sensor.id);
  };

  const handleRandomFaultInjection = async () => {
    setInjecting(true);
    setStatusMsg("Injecting +150 µg/m³ persistent fault across 3 random nodes (10 ticks)...");
    try {
      // Auto-authenticate Admin demo session if not already signed in as admin
      if (!user || user.role !== "admin") {
        await login("admin@vayumesh.in", "Admin@123");
      }
      const res = await triggerFaultInjection(null, 150, 10, 3);
      const names = (res.injected_sensors || [])
        .map((s) => `${s.sensor_name} (${s.final_trust})`)
        .join(", ");
      setStatusMsg(`Quarantined ${res.injected_count} random nodes: ${names}`);

      // Automatically focus & plot the first faulted sensor's live EWMA decay curve
      selectedSensorIdRef.current = res.sensor_id;
      await loadData();
      await loadTrustHistory(res.sensor_id);
    } catch (e) {
      setStatusMsg(`Fault injection failed: ${e.response?.data?.error?.message || e.message}`);
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      {/* Fusion & Map Controls Toolbar */}
      <div className="toolbar-bar">
        <div className="topbar-controls">
          <button
            className="btn danger"
            onClick={handleRandomFaultInjection}
            disabled={injecting}
            title="Randomly picks 3 active sensors and injects +150 µg/m³ bias over 10 ticks"
          >
            <AlertTriangle size={13} />{" "}
            {injecting ? "Injecting 3 Faults..." : "Inject Fault (3 Random Nodes, +150)"}
          </button>

          <button
            className={`btn ${fusionMode === "hybrid" ? "active" : ""}`}
            onClick={() => setFusionMode("hybrid")}
          >
            <Satellite size={13} /> Satellite + Ground
          </button>
          <button
            className={`btn ${fusionMode === "ground_only" ? "active" : ""}`}
            onClick={() => setFusionMode("ground_only")}
          >
            Ground Only
          </button>

          <button className={`btn ${mode === "idw" ? "active" : ""}`} onClick={() => setMode("idw")}>
            <Zap size={13} /> Fast TW-IDW
          </button>
          <button
            className={`btn ${mode === "kriging" ? "active" : ""}`}
            onClick={() => setMode("kriging")}
          >
            <Sliders size={13} /> Precision Kriging
          </button>
          <button
            className={`btn ${showUncertainty ? "active" : ""}`}
            onClick={() => setShowUncertainty((v) => !v)}
          >
            Uncertainty
          </button>
          <button
            className="btn"
            onClick={() => setTileStyle((t) => (t === "street" ? "satellite" : "street"))}
          >
            <Layers size={13} /> {tileStyle === "street" ? "Satellite View" : "Street Map"}
          </button>
          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: "0.74rem",
              color: "#cbd5e1",
            }}
          >
            Opacity {Math.round(overlayOpacity * 100)}%
            <input
              type="range"
              min="0.15"
              max="0.80"
              step="0.05"
              value={overlayOpacity}
              onChange={(e) => setOverlayOpacity(Number(e.target.value))}
              style={{ width: 64 }}
            />
          </label>
          <select
            className="select-input"
            style={{ width: "auto", padding: "5px 8px" }}
            value={gridSize}
            onChange={(e) => setGridSize(Number(e.target.value))}
          >
            <option value={60}>Grid 60×60</option>
            <option value={80}>Grid 80×80</option>
            <option value={100}>Grid 100×100</option>
          </select>
        </div>

        <div className="topbar-controls">
          {(heatmap?.quick_zones || []).map((z) => (
            <button
              key={z.id}
              className="btn"
              onClick={() => setFlyTarget({ ...z, _ts: Date.now() })}
            >
              <MapPin size={12} /> {z.label}
            </button>
          ))}
        </div>
      </div>

      <main className="main-grid">
        <AQIMap
          heatmap={heatmap}
          showUncertainty={showUncertainty}
          overlayOpacity={overlayOpacity}
          selectedSensorId={selectedSensor?.id}
          onSelectSensor={handleSelectSensor}
          flyTarget={flyTarget}
          tileStyle={tileStyle}
        />

        <aside className="sidebar">
          <div className="card">
            <div className="card-title">
              <span>Live Fusion Summary</span>
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
                <div className="metric-label">Coverage</div>
                <div className="metric-value">{heatmap?.coverage_pct ?? "—"}%</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Grid Compute</div>
                <div className="metric-value">{heatmap?.compute_ms ?? "—"} ms</div>
              </div>
            </div>
            <div style={{ fontSize: "0.71rem", color: "#94a3b8", marginTop: 8 }}>
              Ground/Mobile: <strong>{heatmap?.active_sensor_count ?? 0}</strong> · Satellite CAMS
              Anchors: <strong>{heatmap?.satellite_anchors_used ?? 0}</strong>
              <br />
              {statusMsg}
            </div>
          </div>

          <AdvisoryCard advisory={advisory} profile={profile} onProfileChange={setProfile} />

          <div className="card">
            <div className="card-title">
              <span>EWMA Trust Trajectory</span>
              <span style={{ fontSize: "0.68rem", color: "#94a3b8" }}>α = 0.25 · floor 0.05</span>
            </div>
            <SensorTrustChart trustData={trustData} />
          </div>

          <div className="card">
            <div className="card-title">
              <span>Active Corridor Sensor Fleet</span>
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
                    style={{ background: trustColor(s.trust_weight), color: "#ffffff" }}
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
