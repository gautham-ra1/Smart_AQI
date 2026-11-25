// Exact India CPCB NAQI PM2.5 Sub-Index Color Scale (NOT US EPA)
export const CPCB_BANDS = [
  { maxPm25: 30, aqiRange: "0–50", label: "Good", hex: "#00B050", rgb: [0, 176, 80] },
  { maxPm25: 60, aqiRange: "51–100", label: "Satisfactory", hex: "#92D050", rgb: [146, 208, 80] },
  { maxPm25: 90, aqiRange: "101–200", label: "Moderate", hex: "#FFFF00", rgb: [255, 255, 0] },
  { maxPm25: 120, aqiRange: "201–300", label: "Poor", hex: "#FF9900", rgb: [255, 153, 0] },
  { maxPm25: 250, aqiRange: "301–400", label: "Very Poor", hex: "#FF0000", rgb: [255, 0, 0] },
  { maxPm25: 1000, aqiRange: "401–500", label: "Severe", hex: "#C00000", rgb: [192, 0, 0] },
];

export function pm25ToCPCBColor(pm25) {
  const val = Math.max(0, Number(pm25) || 0);
  for (const band of CPCB_BANDS) {
    if (val <= band.maxPm25) return band;
  }
  return CPCB_BANDS[CPCB_BANDS.length - 1];
}

export function trustColor(weight) {
  if (weight >= 0.95) return "#2563eb"; // Official CAAQMS blue
  if (weight >= 0.65) return "#10b981"; // Healthy green
  if (weight >= 0.35) return "#f59e0b"; // Degraded amber
  return "#ef4444"; // Quarantined red
}
