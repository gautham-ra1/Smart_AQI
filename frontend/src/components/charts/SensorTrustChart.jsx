import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";

export default function SensorTrustChart({ trustData }) {
  if (!trustData || !trustData.history?.length) {
    return (
      <div style={{ fontSize: "0.76rem", color: "#94a3b8" }}>
        Click any sensor on the map or list to inspect its EWMA trust trajectory.
      </div>
    );
  }

  const chartData = trustData.history.map((h, i) => ({
    tick: i + 1,
    trust: Number(h.new_trust.toFixed(3)),
    pm25: Number(h.pm25_corrected.toFixed(1)),
    tier: h.tier_used,
  }));

  return (
    <div>
      <div style={{ fontSize: "0.78rem", marginBottom: 6 }}>
        <strong>{trustData.sensor.name}</strong>{" "}
        <span style={{ color: "#94a3b8" }}>
          ({trustData.sensor.sensor_type} · trust {trustData.sensor.trust_weight})
        </span>
      </div>
      <div style={{ width: "100%", height: 135 }}>
        <ResponsiveContainer>
          <LineChart data={chartData}>
            <XAxis dataKey="tick" stroke="#64748b" fontSize={11} />
            <YAxis domain={[0, 1]} stroke="#64748b" fontSize={11} />
            <Tooltip
              contentStyle={{
                background: "#0f172a",
                border: "1px solid #334155",
                fontSize: "12px",
              }}
            />
            <ReferenceLine y={0.2} stroke="#ef4444" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="trust"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
