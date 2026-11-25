import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import HeatmapLayer from "./HeatmapLayer";
import { CPCB_BANDS, trustColor } from "../../utils/aqiColors";

export default function AQIMap({
  heatmap,
  showUncertainty,
  selectedSensorId,
  onSelectSensor,
}) {
  const center = heatmap?.bounds
    ? [heatmap.bounds.center_lat, heatmap.bounds.center_lon]
    : [13.3161, 75.772];

  return (
    <div className="map-pane">
      <div className="map-banner">
        <strong>Chikkamagaluru District</strong>
        <span style={{ color: "#94a3b8" }}>
          {heatmap?.layer_label || "Hyperlocal PM2.5-Equivalent AQI (Real-Time Sub-Index)"}
        </span>
        {heatmap && (
          <span className="brand-pill">
            {heatmap.mode_used.toUpperCase()} · {heatmap.compute_ms} ms
          </span>
        )}
      </div>

      <MapContainer
        center={center}
        zoom={12}
        style={{ height: "100%", width: "100%", background: "#0b1120" }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors &copy; CARTO"
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {heatmap && (
          <HeatmapLayer
            gridPm25={heatmap.grid_pm25}
            gridStdDev={heatmap.grid_std_dev}
            bounds={heatmap.bounds}
            showUncertainty={showUncertainty}
          />
        )}

        {(heatmap?.sensors || []).map((s) => {
          const isSelected = s.id === selectedSensorId;
          const color = trustColor(s.trust_weight);
          const isOfficial = s.sensor_type === "official";
          return (
            <CircleMarker
              key={s.id}
              center={[s.lat, s.lon]}
              radius={isOfficial ? 10 : isSelected ? 9 : 7}
              pathOptions={{
                color: isSelected ? "#ffffff" : color,
                fillColor: color,
                fillOpacity: 0.92,
                weight: isSelected ? 3 : 2,
              }}
              eventHandlers={{
                click: () => onSelectSensor(s),
              }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                <div style={{ fontSize: "12px", lineHeight: 1.35 }}>
                  <strong>{s.name}</strong>
                  <br />
                  Type: {s.sensor_type} | Tier: {s.tier_used}
                  <br />
                  Raw PM2.5: {s.pm25_raw} | RH-Corr: {s.pm25_corrected} µg/m³ (RH {s.rh_pct}%)
                  <br />
                  Trust Weight: <strong>{s.trust_weight}</strong> ({s.status})
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>

      <div className="map-legend">
        <div style={{ fontWeight: 700, color: "#cbd5e1" }}>
          CPCB National AQI (PM2.5 Sub-Index)
        </div>
        <div className="legend-row">
          {CPCB_BANDS.map((b) => (
            <span className="legend-chip" key={b.label}>
              <span className="legend-dot" style={{ background: b.hex }} />
              {b.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
