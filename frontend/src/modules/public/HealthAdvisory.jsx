import { useEffect, useState } from "react";
import { fetchAdvisory } from "../../services/api";
import { CPCB_BANDS } from "../../utils/aqiColors";

const COHORTS = [
  { id: "general", label: "General Public" },
  { id: "asthma", label: "Asthma / COPD" },
  { id: "children", label: "Children (<5 / School)" },
  { id: "elderly", label: "Elderly Adults" },
  { id: "pregnant", label: "Pregnant Women" },
  { id: "outdoor_worker", label: "Outdoor Workers (Bus / Auto / Traffic)" },
];

export default function HealthAdvisory() {
  const [pm25, setPm25] = useState(75);
  const [results, setResults] = useState([]);

  useEffect(() => {
    let active = true;
    Promise.all(COHORTS.map((c) => fetchAdvisory(c.id, 13.3161, 75.772, pm25)))
      .then((res) => {
        if (active) setResults(res);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [pm25]);

  return (
    <div className="page-container">
      <h2 style={{ marginBottom: 6 }}>India CPCB NAQI & MoHFW / NCDC Personalised Advisories</h2>
      <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: 16 }}>
        Vulnerable Indian cohorts escalate protective actions 1–2 CPCB AQI bands earlier than healthy adults.
      </p>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">
          <span>Interactive PM2.5 Exposure Simulator</span>
          <span className="brand-pill">PM2.5 = {pm25} µg/m³</span>
        </div>
        <input
          type="range"
          min="5"
          max="320"
          value={pm25}
          onChange={(e) => setPm25(Number(e.target.value))}
          style={{ width: "100%" }}
        />
        <div className="legend-row" style={{ marginTop: 8, flexWrap: "wrap" }}>
          {CPCB_BANDS.map((b) => (
            <span className="legend-chip" key={b.label} style={{ fontSize: "0.75rem" }}>
              <span className="legend-dot" style={{ background: b.hex }} />
              {b.label} ({b.minPm25}–{b.maxPm25} µg/m³ / AQI {b.aqiRange})
            </span>
          ))}
        </div>
      </div>

      <div className="grid-2">
        {results.map((adv, idx) => (
          <div className="card" key={COHORTS[idx].id}>
            <div className="card-title">
              <span>{COHORTS[idx].label}</span>
              <span
                className="badge"
                style={{
                  background: adv.band_color,
                  color: adv.aqi_pm25_equiv <= 200 ? "#0b1120" : "#ffffff",
                }}
              >
                AQI {adv.aqi_pm25_equiv} · {adv.cpcb_band}
              </span>
            </div>
            <div style={{ color: "#38bdf8", fontWeight: 700, fontSize: "0.85rem", marginBottom: 6 }}>
              {adv.action_tier}
            </div>
            <p style={{ fontSize: "0.82rem", marginBottom: 8 }}>{adv.advisory}</p>
            <ul style={{ paddingLeft: 18, fontSize: "0.78rem", color: "#cbd5e1" }}>
              {adv.checklist.map((item, i) => (
                <li key={i} style={{ marginBottom: 3 }}>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
