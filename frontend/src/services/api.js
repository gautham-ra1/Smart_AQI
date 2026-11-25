import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 12000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("vayumesh_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function fetchHeatmap(mode = "kriging", city = "chikkamagaluru") {
  const { data } = await api.get("/api/v1/heatmap", { params: { city, mode, grid_size: 50 } });
  return data.data;
}

export async function fetchAdvisory(profile = "general", lat = 13.3161, lon = 75.772) {
  const { data } = await api.get("/api/v1/advisories", {
    params: { profile, lat, lon, city: "chikkamagaluru" },
  });
  return data.data;
}

export async function fetchSensorTrustHistory(sensorId) {
  const { data } = await api.get(`/api/v1/sensors/${sensorId}/trust-history`);
  return data.data;
}

export async function loginAccount(email, password) {
  const { data } = await api.post("/api/v1/auth/login", { email, password });
  localStorage.setItem("vayumesh_token", data.data.access_token);
  localStorage.setItem("vayumesh_user", JSON.stringify(data.data.user));
  return data.data;
}

export async function triggerFaultInjection(sensorId = null, biasPm25 = 150, ticks = 10) {
  const { data } = await api.post("/api/v1/admin/fault-injection", {
    sensor_id: sensorId,
    city: "chikkamagaluru",
    bias_pm25: biasPm25,
    ticks,
  });
  return data.data;
}

export async function triggerRecompute(mode = "kriging") {
  const { data } = await api.post("/api/v1/admin/recompute", {
    city: "chikkamagaluru",
    mode,
    grid_size: 50,
  });
  return data.data;
}

export default api;
