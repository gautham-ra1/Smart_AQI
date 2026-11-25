import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { pm25ToCPCBColor } from "../../utils/aqiColors";

/**
 * Renders the 50x50 NumPy/SciPy interpolated PM2.5 matrix onto an HTML5 Canvas
 * Leaflet ImageOverlay mapped strictly to India CPCB NAQI color bands.
 * Avoids Leaflet.heat point-density distortion.
 */
export default function HeatmapLayer({ gridPm25, gridStdDev, bounds, showUncertainty }) {
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
        const band = pm25ToCPCBColor(pm25);
        const [red, green, blue] = band.rgb;

        // Modulate opacity by Kriging uncertainty if enabled (higher std_dev -> lower alpha)
        let alpha = 148;
        if (showUncertainty && gridStdDev && gridStdDev[r] && gridStdDev[r][c] != null) {
          const std = Number(gridStdDev[r][c]);
          const confidence = Math.max(0.28, Math.min(1.0, 1.0 - std / 24.0));
          alpha = Math.round(180 * confidence);
        }

        const idx = (r * cols + c) * 4;
        imgData.data[idx] = red;
        imgData.data[idx + 1] = green;
        imgData.data[idx + 2] = blue;
        imgData.data[idx + 3] = alpha;
      }
    }

    ctx.putImageData(imgData, 0, 0);

    // Upscale smoothly onto a 250x250 canvas for crisp contour rendering
    const smoothCanvas = document.createElement("canvas");
    smoothCanvas.width = 250;
    smoothCanvas.height = 250;
    const sCtx = smoothCanvas.getContext("2d");
    sCtx.imageSmoothingEnabled = true;
    sCtx.imageSmoothingQuality = "high";
    sCtx.drawImage(canvas, 0, 0, 250, 250);

    const dataUrl = smoothCanvas.toDataURL("image/png");
    const leafletBounds = [
      [bounds.min_lat, bounds.min_lon],
      [bounds.max_lat, bounds.max_lon],
    ];

    if (overlayRef.current) {
      overlayRef.current.setUrl(dataUrl);
      overlayRef.current.setBounds(leafletBounds);
    } else {
      overlayRef.current = L.imageOverlay(dataUrl, leafletBounds, {
        opacity: 0.78,
        interactive: false,
      }).addTo(map);
    }
  }, [gridPm25, gridStdDev, bounds, showUncertainty, map]);

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
