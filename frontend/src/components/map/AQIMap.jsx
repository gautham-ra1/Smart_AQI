import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Polyline,
  Popup,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import HeatmapLayer from "./HeatmapLayer";
import { CPCB_BANDS, trustColor } from "../../utils/aqiColors";
import { fetchPointAQI } from "../../services/api";

function MapFlyController({ target }) {
  const map = useMap();
  if (target) {
    map.flyTo([target.lat, target.lon], target.zoom, { duration: 0.9 });
  }
  return null;
}

function ClickInspector({ onInspect }) {
  useMapEvents({
    click: async (e) => {
      try {
        const res = await fetchPointAQI(e.latlng.lat, e.latlng.lng);
        onInspect(res);
      } catch {
        // Ignore outside-bounds clicks
      }
    },
  });
  return null;
}

export default function AQIMap({
  heatmap,
  showUncertainty,
  overlayOpacity = 0.45,
  selectedSensorId,
  onSelectSensor,
  flyTarget,
  tileStyle = "street",
}) {
  const [clickedPoint, setClickedPoint] = useState(null);

  const center = heatmap?.bounds
    ? [heatmap.bounds.center_lat, heatmap.bounds.center_lon]
    : [13.36, 75.53];

  // 100% API-key-free crisp tile sources: OpenStreetMap (streets/labels) & Esri World Imagery (satellite)
  const tileUrl =
    tileStyle === "satellite"
      ? "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      : "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

  const tileAttribution =
    tileStyle === "satellite"
      ? "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics"
      : "&copy; OpenStreetMap contributors";

  return (
    <div className="map-pane">
      <div className="map-banner">
        <strong>Chikkamagaluru – Sringeri Corridor</strong>
        <span style={{ color: "#94a3b8" }}>
          {heatmap?.layer_label || "Hyperlocal PM2.5-Equivalent AQI (Real-Time Sub-Index)"}
        </span>
        {heatmap && (
          <>
            <span className="brand-pill">
              {heatmap.mode_used.toUpperCase()} {heatmap.grid_size}×{heatmap.grid_size} ·{" "}
              {heatmap.compute_ms} ms
            </span>
            <span
              className="brand-pill"
              style={{
                background:
                  heatmap.fusion_mode === "hybrid"
                    ? "rgba(16,185,129,0.18)"
                    : "rgba(245,158,11,0.18)",
                color: heatmap.fusion_mode === "hybrid" ? "#6ee7b7" : "#fcd34d",
                borderColor:
                  heatmap.fusion_mode === "hybrid"
                    ? "rgba(16,185,129,0.4)"
                    : "rgba(245,158,11,0.4)",
              }}
            >
              {heatmap.fusion_mode === "hybrid"
                ? `Satellite + Ground · ${heatmap.coverage_pct}% Coverage`
                : `Ground Only · ${heatmap.empty_pixels} Empty Pixels`}
            </span>
          </>
        )}
      </div>

      <MapContainer
        center={center}
        zoom={10}
        style={{ height: "100%", width: "100%", background: "#0b1120" }}
      >
        <TileLayer
          key={tileStyle}
          attribution={tileAttribution}
          url={tileUrl}
          maxZoom={19}
        />

        <MapFlyController target={flyTarget} />
        <ClickInspector onInspect={setClickedPoint} />

        {heatmap && (
          <HeatmapLayer
            gridPm25={heatmap.grid_pm25}
            gridStdDev={heatmap.grid_std_dev}
            bounds={heatmap.bounds}
            showUncertainty={showUncertainty}
            overlayOpacity={overlayOpacity}
          />
        )}

        {/* Live Mobile Transit GPS Breadcrumb Trails (4 Travelling Vehicles) */}
        {(heatmap?.mobile_trails || []).map((trail, idx) => {
          const trailColors = ["#38bdf8", "#facc15", "#c084fc", "#fb923c"];
          return (
            <Polyline
              key={trail.sensor_id}
              positions={trail.points.map((p) => [p.lat, p.lon])}
              pathOptions={{
                color: trailColors[idx % trailColors.length],
                weight: 3.5,
                opacity: 0.9,
                dashArray: "7 6",
              }}
            />
          );
        })}

        {/* Sensor Markers */}
        {(heatmap?.sensors || []).map((s) => {
          const isSelected = s.id === selectedSensorId;
          const color = trustColor(s.trust_weight);
          const isOfficial = s.sensor_type === "official";
          const isMobile = s.sensor_type === "mobile_fleet";
          return (
            <CircleMarker
              key={s.id}
              center={[s.lat, s.lon]}
              radius={isOfficial ? 10 : isMobile ? 8 : isSelected ? 9 : 6.5}
              pathOptions={{
                color: isSelected ? "#ffffff" : isMobile ? "#38bdf8" : color,
                fillColor: color,
                fillOpacity: 0.94,
                weight: isSelected || isMobile ? 3 : 2,
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
                  {isOfficial && s.model_meta?.live_source && (
                    <>
                      <br />
                      Live Feed: <strong>{s.model_meta.live_source}</strong>
                    </>
                  )}
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

        {/* Click-Anywhere Hyperlocal AQI Popup */}
        {clickedPoint && (
          <Popup
            position={[clickedPoint.lat, clickedPoint.lon]}
            eventHandlers={{ remove: () => setClickedPoint(null) }}
          >
            <div style={{ fontSize: "12px", lineHeight: 1.4, minWidth: 200 }}>
              <strong>Hyperlocal Point Estimate</strong>
              <br />
              Coords: {clickedPoint.lat}, {clickedPoint.lon}
              <br />
              PM2.5: <strong>{clickedPoint.pm25_equiv} µg/m³</strong> (CPCB AQI{" "}
              <strong>{clickedPoint.aqi_pm25_equiv}</strong> · {clickedPoint.cpcb_band})
              {clickedPoint.uncertainty_std_dev != null && (
                <>
                  <br />
                  Kriging Uncertainty: <strong>±{clickedPoint.uncertainty_std_dev} µg/m³</strong>
                </>
              )}
              <br />
              <span style={{ color: "#475569", fontSize: "11px" }}>
                {clickedPoint.data_source}
              </span>
            </div>
          </Popup>
        )}
      </MapContainer>

      <div className="map-legend">
        <div style={{ fontWeight: 700, color: "#cbd5e1" }}>
          CPCB National AQI (PM2.5 Sub-Index) · Click anywhere on map to inspect
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
