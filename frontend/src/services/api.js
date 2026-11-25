import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("vayumesh_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function fetchHeatmap({
  mode = "kriging",
  fusionMode = "hybrid",
  gridSize = 80,
  city = "chikkamagaluru",
} = {}) {
  const { data } = await api.get("/api/v1/heatmap", {
    params: { city, mode, fusion_mode: fusionMode, grid_size: gridSize },
  });
  return data.data;
}

export async function fetchPointAQI(lat, lon, city = "chikkamagaluru") {
  const { data } = await api.get("/api/v1/aqi/point", { params: { lat, lon, city } });
  return data.data;
}

export async function fetchAQIHistory(city = "chikkamagaluru", limit = 30) {
  const { data } = await api.get("/api/v1/aqi/history", { params: { city, limit } });
  return data.data;
}

export async function fetchAdvisory(profile = "general", lat = 13.3161, lon = 75.772, pm25 = null) {
  const params = { profile, city: "chikkamagaluru" };
  if (pm25 != null) params.pm25 = pm25;
  else {
    params.lat = lat;
    params.lon = lon;
  }
  const { data } = await api.get("/api/v1/advisories", { params });
  return data.data;
}

export async function fetchSensorTrustHistory(sensorId) {
  const { data } = await api.get(`/api/v1/sensors/${sensorId}/trust-history`);
  return data.data;
}

export async function fetchAnalyticsSummary() {
  const { data } = await api.get("/api/v1/analytics/summary");
  return data.data;
}

export async function registerAccount(payload) {
  const { data } = await api.post("/api/v1/auth/register", payload);
  localStorage.setItem("vayumesh_token", data.data.access_token);
  localStorage.setItem("vayumesh_user", JSON.stringify(data.data.user));
  return data.data;
}

export async function loginAccount(email, password) {
  const { data } = await api.post("/api/v1/auth/login", { email, password });
  localStorage.setItem("vayumesh_token", data.data.access_token);
  localStorage.setItem("vayumesh_user", JSON.stringify(data.data.user));
  return data.data;
}

export async function fetchMe() {
  const { data } = await api.get("/api/v1/auth/me");
  return data.data;
}

export async function updateCitizenProfile(payload) {
  const { data } = await api.patch("/api/v1/citizens/profile", payload);
  return data.data;
}

export async function fetchMySensors() {
  const { data } = await api.get("/api/v1/citizens/my-sensors");
  return data.data;
}

export async function fetchMyReadings() {
  const { data } = await api.get("/api/v1/citizens/my-readings");
  return data.data;
}

export async function registerSensor(payload) {
  const { data } = await api.post("/api/v1/sensors/register", payload);
  return data.data;
}

export async function triggerFaultInjection(sensorId = null, biasPm25 = 150, ticks = 10, count = 3) {
  const { data } = await api.post("/api/v1/admin/fault-injection", {
    sensor_id: sensorId,
    city: "chikkamagaluru",
    count,
    bias_pm25: biasPm25,
    ticks,
  });
  return data.data;
}

export async function triggerRecompute(mode = "kriging", timestamp = null, gridSize = 80) {
  const body = { city: "chikkamagaluru", mode, grid_size: gridSize };
  if (timestamp) body.timestamp = timestamp;
  const { data } = await api.post("/api/v1/admin/recompute", body);
  return data.data;
}

export async function triggerSyncOfficial() {
  const { data } = await api.post("/api/v1/admin/sync-official", null, {
    params: { city: "chikkamagaluru" },
  });
  return data.data;
}

export async function fetchAdminOverview() {
  const { data } = await api.get("/api/v1/admin/overview");
  return data.data;
}

export async function fetchAdminAuditLogs() {
  const { data } = await api.get("/api/v1/admin/audit-logs");
  return data.data;
}

export async function fetchAdminUsers() {
  const { data } = await api.get("/api/v1/admin/users");
  return data.data;
}

export default api;
