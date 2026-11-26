// Exact India CPCB NAQI PM2.5 Sub-Index Color Scale (NOT US EPA)
export const CPCB_BANDS = [
  { minPm25: 0, maxPm25: 30, aqiRange: "0–50", label: "Good", hex: "#00B050", rgb: [0, 176, 80] },
  { minPm25: 30, maxPm25: 60, aqiRange: "51–100", label: "Satisfactory", hex: "#92D050", rgb: [146, 208, 80] },
  { minPm25: 60, maxPm25: 90, aqiRange: "101–200", label: "Moderate", hex: "#FFFF00", rgb: [255, 235, 20] },
  { minPm25: 90, maxPm25: 120, aqiRange: "201–300", label: "Poor", hex: "#FF9900", rgb: [255, 153, 0] },
  { minPm25: 120, maxPm25: 250, aqiRange: "301–400", label: "Very Poor", hex: "#FF0000", rgb: [255, 40, 40] },
  { minPm25: 250, maxPm25: 500, aqiRange: "401–500", label: "Severe", hex: "#C00000", rgb: [192, 0, 32] },
];

// Smooth continuous color stops anchored at CPCB breakpoints for high-res Canvas gradients
const GRADIENT_STOPS = [
  [0, [0, 165, 85]],
  [15, [16, 185, 95]],
  [30, [110, 205, 80]],
  [60, [215, 225, 45]],
  [90, [255, 190, 15]],
  [120, [255, 115, 15]],
  [200, [245, 35, 35]],
  [350, [185, 0, 35]],
];

export function pm25ToSmoothRGB(pm25) {
  const v = Math.max(0, Number(pm25) || 0);
  if (v <= GRADIENT_STOPS[0][0]) return GRADIENT_STOPS[0][1];
  for (let i = 1; i < GRADIENT_STOPS.length; i++) {
    const [x1, c1] = GRADIENT_STOPS[i - 1];
    const [x2, c2] = GRADIENT_STOPS[i];
    if (v <= x2) {
      const t = (v - x1) / (x2 - x1);
      return [
        Math.round(c1[0] + (c2[0] - c1[0]) * t),
        Math.round(c1[1] + (c2[1] - c1[1]) * t),
        Math.round(c1[2] + (c2[2] - c1[2]) * t),
      ];
    }
  }
  return GRADIENT_STOPS[GRADIENT_STOPS.length - 1][1];
}

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
