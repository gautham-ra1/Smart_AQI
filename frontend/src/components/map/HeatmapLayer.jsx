import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { pm25ToSmoothRGB } from "../../utils/aqiColors";

/**
 * High-Resolution (512x512) HTML5 Canvas Leaflet ImageOverlay.
 * Translucent CPCB color wash so underlying roads, rivers, and town names
 * (Chikkamagaluru, Aldur, Balehonnur, Koppa, Sringeri) remain razor-sharp.
 */
export default function HeatmapLayer({
  gridPm25,
  gridStdDev,
  bounds,
  showUncertainty,
  overlayOpacity = 0.45,
}) {
  const map = useMap();
  const overlayRef = useRef(null);

  useEffect(() => {
    if (!gridPm25 || !gridPm25.length || !bounds) return;

    const rows = gridPm25.length;
    const cols = gridPm25[0].length;

    const canvas = document.createElement("canvas");
    canvas.width = cols;
    canvas.height = rows;
    const ctx = canvas.getContext("2d");
    const imgData = ctx.createImageData(cols, rows);

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const pm25 = gridPm25[r][c];
        const idx = (r * cols + c) * 4;

        // Empty pixel (unmonitored rural zone in ground_only mode)
        if (pm25 == null) {
          imgData.data[idx] = 0;
          imgData.data[idx + 1] = 0;
          imgData.data[idx + 2] = 0;
          imgData.data[idx + 3] = 0;
          continue;
        }

        const [red, green, blue] = pm25ToSmoothRGB(pm25);

        let alpha = 210;
        if (showUncertainty && gridStdDev && gridStdDev[r] && gridStdDev[r][c] != null) {
          const std = Number(gridStdDev[r][c]);
          // High confidence near ground/mobile sensors -> clearer tint; satellite-only -> softer tint
          const confidence = Math.max(0.42, Math.min(1.0, 1.0 - std / 30.0));
          alpha = Math.round(235 * confidence);
        }

        imgData.data[idx] = red;
        imgData.data[idx + 1] = green;
        imgData.data[idx + 2] = blue;
        imgData.data[idx + 3] = alpha;
      }
    }

    ctx.putImageData(imgData, 0, 0);

    const smoothCanvas = document.createElement("canvas");
    smoothCanvas.width = 512;
    smoothCanvas.height = 512;
    const sCtx = smoothCanvas.getContext("2d");
    sCtx.imageSmoothingEnabled = true;
    sCtx.imageSmoothingQuality = "high";
    sCtx.drawImage(canvas, 0, 0, 512, 512);

    const dataUrl = smoothCanvas.toDataURL("image/png");
    const leafletBounds = [
      [bounds.min_lat, bounds.min_lon],
      [bounds.max_lat, bounds.max_lon],
    ];

    if (overlayRef.current) {
      overlayRef.current.setUrl(dataUrl);
      overlayRef.current.setBounds(leafletBounds);
      overlayRef.current.setOpacity(overlayOpacity);
    } else {
      overlayRef.current = L.imageOverlay(dataUrl, leafletBounds, {
        opacity: overlayOpacity,
        interactive: false,
      }).addTo(map);
    }
  }, [gridPm25, gridStdDev, bounds, showUncertainty, overlayOpacity, map]);

  useEffect(() => {
    return () => {
      if (overlayRef.current) {
        map.removeLayer(overlayRef.current);
        overlayRef.current = null;
      }
    };
  }, [map]);

  return null;
}
