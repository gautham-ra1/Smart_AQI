import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { fetchAQIHistory, fetchAnalyticsSummary } from "../../services/api";

export default function AQIHistory() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetchAnalyticsSummary().then(setSummary).catch(() => {});
    fetchAQIHistory("chikkamagaluru", 25).then(setHistory).catch(() => {});
  }, []);

  const trendData = (summary?.recent_trend || []).map((t, i) => ({
    idx: i + 1,
    pm25: Number(t.pm25_corrected),
    trust: Number(t.new_trust),
    tier: t.tier_used,
  }));

  return (
    <div className="page-container">
      <h2 style={{ marginBottom: 6 }}>Corridor Telemetry History & Adaptive Fusion Architecture</h2>
      <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: 16 }}>
        Chikkamagaluru – Balehonnur – Sringeri real-time analytics backed by immutable PostgreSQL raw telemetry.
      </p>

      <div className="metric-row" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 16 }}>
        <div className="metric-box">
          <div className="metric-label">Total Active Fleet</div>
          <div className="metric-value">{summary?.total_sensors ?? "—"}</div>
        </div>
        <div className="metric-box">
          <div className="metric-label">Immutable Raw Readings</div>
          <div className="metric-value">{summary?.immutable_raw_readings ?? "—"}</div>
        </div>
        <div className="metric-box">
          <div className="metric-label">Mean Fleet Trust</div>
          <div className="metric-value">{summary?.mean_trust_weight ?? "—"}</div>
        </div>
        <div className="metric-box">
          <div className="metric-label">Tier Evaluations</div>
          <div className="metric-value">
            {summary?.evaluations_by_tier
              ? Object.entries(summary.evaluations_by_tier)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")
              : "—"}
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-title">Recent RH-Corrected PM2.5 Stream (µg/m³)</div>
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <AreaChart data={trendData}>
                <XAxis dataKey="idx" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #334155", fontSize: 12 }}
                />
                <Area type="monotone" dataKey="pm25" stroke="#38bdf8" fill="rgba(56,189,248,0.22)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Why VayuMesh Works Across Rural Western Ghats</div>
          <ul style={{ paddingLeft: 18, fontSize: "0.82rem", color: "#cbd5e1", lineHeight: 1.65 }}>
            <li>
              <strong>Cold-Start Solution:</strong> Fuses 1 official KSPCB CAAQMS (Kalyana Nagara) with
              institutional anchors, moving KSRTC buses/autos, and a 5×5 Open-Meteo CAMS satellite prior
              covering Sringeri & Koppa with zero empty pixels.
            </li>
            <li>
              <strong>Monsoon Hygrometric Pre-Calibration:</strong> Damps optical Mie scattering above
              75% RH so Western Ghats fog does not falsely penalize healthy sensors.
            </li>
            <li>
              <strong>Two-Tier EWMA Trust Engine:</strong> Reference-anchored within 5 km, Peer-MAD
              consensus beyond 5 km, automatically quarantining persistent faults to weight 0.05.
            </li>
            <li>
              <strong>Immutable Auditability:</strong> PostgreSQL <code>BEFORE UPDATE OR DELETE</code>{" "}
              trigger guarantees raw sensor telemetry can never be altered and grids can be replayed at any timestamp.
            </li>
          </ul>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Persisted Interpolation Grid Runs (Replayable)</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Grid ID</th>
              <th>Mode Used</th>
              <th>Resolution</th>
              <th>Active Sensors</th>
              <th>Compute (ms)</th>
              <th>Computed At</th>
            </tr>
          </thead>
          <tbody>
            {history.map((g) => (
              <tr key={g.id}>
                <td>#{g.id}</td>
                <td>{g.mode.toUpperCase()}</td>
                <td>
                  {g.grid_size}×{g.grid_size}
                </td>
                <td>{g.active_sensor_count}</td>
                <td>{g.compute_ms} ms</td>
                <td>{new Date(g.computed_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
