const PROFILES = [
  { value: "general", label: "General Public" },
  { value: "asthma", label: "Asthma / COPD" },
  { value: "children", label: "Children (<5 / School)" },
  { value: "elderly", label: "Elderly Adults" },
  { value: "pregnant", label: "Pregnant Women" },
  { value: "outdoor_worker", label: "Outdoor Workers (Auto / Traffic)" },
];

export default function AdvisoryCard({ advisory, profile, onProfileChange }) {
  return (
    <div className="card">
      <div className="card-title">
        <span>MoHFW / CPCB Health Advisory</span>
        {advisory && (
          <span
            className="badge"
            style={{
              background: advisory.band_color,
              color: advisory.aqi_pm25_equiv <= 200 ? "#0b1120" : "#ffffff",
            }}
          >
            AQI {advisory.aqi_pm25_equiv} · {advisory.cpcb_band}
          </span>
        )}
      </div>

      <div style={{ marginBottom: 8 }}>
        <select
          className="select-input"
          value={profile}
          onChange={(e) => onProfileChange(e.target.value)}
        >
          {PROFILES.map((p) => (
            <option key={p.value} value={p.value}>
              Cohort: {p.label}
            </option>
          ))}
        </select>
      </div>

      {advisory ? (
        <>
          <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#38bdf8", marginBottom: 4 }}>
            Action Tier: {advisory.action_tier}
          </div>
          <p style={{ fontSize: "0.78rem", marginBottom: 6 }}>{advisory.advisory}</p>
          <ul style={{ paddingLeft: 16, fontSize: "0.74rem", color: "#cbd5e1" }}>
            {advisory.checklist.map((item, idx) => (
              <li key={idx} style={{ marginBottom: 3 }}>
                {item}
              </li>
            ))}
          </ul>
          <div className="disclaimer">{advisory.disclaimer}</div>
        </>
      ) : (
        <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>Loading advisory...</div>
      )}
    </div>
  );
}
