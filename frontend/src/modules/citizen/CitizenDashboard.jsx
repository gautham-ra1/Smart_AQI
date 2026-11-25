import { useEffect, useState } from "react";
import { Copy, KeyRound, PlusCircle, Radio } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import {
  API_BASE_URL,
  fetchMyReadings,
  fetchMySensors,
  registerSensor,
  updateCitizenProfile,
} from "../../services/api";

export default function CitizenDashboard() {
  const { user, setUser, login, register } = useAuth();
  const [authTab, setAuthTab] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [healthProfile, setHealthProfile] = useState(user?.health_profile || "asthma");
  const [msg, setMsg] = useState("");

  // Sensor registration state
  const [sensorName, setSensorName] = useState("");
  const [sensorType, setSensorType] = useState("institutional_node");
  const [lat, setLat] = useState("13.4198"); // Default Sringeri
  const [lon, setLon] = useState("75.2528");
  const [issuedKey, setIssuedKey] = useState(null);
  const [mySensors, setMySensors] = useState([]);
  const [myReadings, setMyReadings] = useState([]);

  const loadPersonal = async () => {
    try {
      const [s, r] = await Promise.all([fetchMySensors(), fetchMyReadings()]);
      setMySensors(s);
      setMyReadings(r);
    } catch {
      // Ignore if unauthenticated
    }
  };

  useEffect(() => {
    if (user) {
      setHealthProfile(user.health_profile || "general");
      loadPersonal();
    }
  }, [user]);

  const handleAuth = async (e) => {
    e.preventDefault();
    setMsg("");
    try {
      if (authTab === "login") {
        await login(email, password);
      } else {
        await register({ email, full_name: fullName, password, health_profile: healthProfile });
      }
      setMsg("Signed in successfully.");
    } catch (err) {
      setMsg(err.response?.data?.error?.message || err.message);
    }
  };

  const handleDemoLogin = async (demoEmail, demoPass) => {
    try {
      await login(demoEmail, demoPass);
      setMsg(`Signed in as ${demoEmail}`);
    } catch (err) {
      setMsg(err.response?.data?.error?.message || err.message);
    }
  };

  const handleProfileSave = async () => {
    try {
      const updated = await updateCitizenProfile({ health_profile: healthProfile });
      setUser(updated);
      localStorage.setItem("vayumesh_user", JSON.stringify(updated));
      setMsg("Saved personal health cohort.");
    } catch (err) {
      setMsg(err.response?.data?.error?.message || err.message);
    }
  };

  const handleRegisterSensor = async (e) => {
    e.preventDefault();
    setMsg("");
    try {
      const res = await registerSensor({
        name: sensorName,
        city: "chikkamagaluru",
        sensor_type: sensorType,
        lat: Number(lat),
        lon: Number(lon),
        model_meta: { module: "PMS5003", registered_via: "Citizen Portal" },
      });
      setIssuedKey(res);
      setSensorName("");
      await loadPersonal();
    } catch (err) {
      setMsg(err.response?.data?.error?.message || err.message);
    }
  };

  if (!user) {
    return (
      <div className="page-container" style={{ maxWidth: 520 }}>
        <div className="card">
          <div className="card-title">
            <span>Citizen & IoT Sensor Owner Portal</span>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                className={`btn ${authTab === "login" ? "active" : ""}`}
                onClick={() => setAuthTab("login")}
              >
                Login
              </button>
              <button
                className={`btn ${authTab === "register" ? "active" : ""}`}
                onClick={() => setAuthTab("register")}
              >
                Register
              </button>
            </div>
          </div>

          <form onSubmit={handleAuth}>
            {authTab === "register" && (
              <div className="form-group">
                <label>Full Name</label>
                <input
                  className="text-input"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>
            )}
            <div className="form-group">
              <label>Email</label>
              <input
                className="text-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                className="text-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {authTab === "register" && (
              <div className="form-group">
                <label>MoHFW Health Cohort</label>
                <select
                  className="select-input"
                  value={healthProfile}
                  onChange={(e) => setHealthProfile(e.target.value)}
                >
                  <option value="general">General Public</option>
                  <option value="asthma">Asthma / COPD</option>
                  <option value="children">Children (&lt;5 / School)</option>
                  <option value="elderly">Elderly Adults</option>
                  <option value="pregnant">Pregnant Women</option>
                  <option value="outdoor_worker">Outdoor Worker</option>
                </select>
              </div>
            )}
            <button className="btn active" type="submit" style={{ width: "100%", justifyContent: "center" }}>
              {authTab === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              className="btn"
              onClick={() => handleDemoLogin("owner@vayumesh.in", "Owner@123")}
            >
              Demo Sensor Owner Login
            </button>
            <button
              className="btn"
              onClick={() => handleDemoLogin("citizen@vayumesh.in", "Citizen@123")}
            >
              Demo Citizen Login
            </button>
          </div>
          {msg && <p style={{ marginTop: 10, fontSize: "0.78rem", color: "#fca5a5" }}>{msg}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h2 style={{ marginBottom: 12 }}>Citizen & IoT Sensor Owner Portal</h2>
      {msg && <div className="card" style={{ marginBottom: 12, color: "#6ee7b7", fontSize: "0.82rem" }}>{msg}</div>}

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-title">
            <span>My Profile & Health Cohort</span>
            <span className="brand-pill">{user.role}</span>
          </div>
          <p style={{ fontSize: "0.82rem", marginBottom: 10 }}>
            <strong>{user.full_name}</strong> · {user.email}
          </p>
          <div className="form-group">
            <label>Saved MoHFW Cohort</label>
            <select
              className="select-input"
              value={healthProfile}
              onChange={(e) => setHealthProfile(e.target.value)}
            >
              <option value="general">General Public</option>
              <option value="asthma">Asthma / COPD</option>
              <option value="children">Children (&lt;5 / School)</option>
              <option value="elderly">Elderly Adults</option>
              <option value="pregnant">Pregnant Women</option>
              <option value="outdoor_worker">Outdoor Worker</option>
            </select>
          </div>
          <button className="btn active" onClick={handleProfileSave}>
            Save Cohort
          </button>
        </div>

        <div className="card">
          <div className="card-title">
            <span>
              <PlusCircle size={13} /> Register New IoT Sensor (One-Time HMAC Key)
            </span>
          </div>
          <form onSubmit={handleRegisterSensor}>
            <div className="form-group">
              <label>Sensor Name</label>
              <input
                className="text-input"
                placeholder="e.g., Sringeri Bus Stand PMS5003"
                value={sensorName}
                onChange={(e) => setSensorName(e.target.value)}
                required
              />
            </div>
            <div className="grid-2" style={{ gap: 8 }}>
              <div className="form-group">
                <label>Sensor Type</label>
                <select
                  className="select-input"
                  value={sensorType}
                  onChange={(e) => setSensorType(e.target.value)}
                >
                  <option value="institutional_node">Institutional Anchor</option>
                  <option value="citizen_fixed">Citizen Fixed</option>
                  <option value="mobile_fleet">Mobile Fleet (Bus / Auto)</option>
                </select>
              </div>
              <div className="form-group">
                <label>Latitude / Longitude (India)</label>
                <div style={{ display: "flex", gap: 6 }}>
                  <input className="text-input" style={{ width: "50%" }} value={lat} onChange={(e) => setLat(e.target.value)} required />
                  <input className="text-input" style={{ width: "50%" }} value={lon} onChange={(e) => setLon(e.target.value)} required />
                </div>
              </div>
            </div>
            <button className="btn active" type="submit">
              <KeyRound size={13} /> Register & Generate One-Time API Key
            </button>
          </form>
        </div>
      </div>

      {/* One-Time API Key Modal Banner */}
      {issuedKey && (
        <div className="card" style={{ marginBottom: 16, borderColor: "#10b981", background: "rgba(16,185,129,0.08)" }}>
          <div className="card-title" style={{ color: "#6ee7b7" }}>
            <span>One-Time Sensor API Key Issued — Copy Now!</span>
            <button
              className="btn active"
              onClick={() => navigator.clipboard.writeText(issuedKey.api_key)}
            >
              <Copy size={12} /> Copy Key
            </button>
          </div>
          <p style={{ fontSize: "0.78rem", color: "#cbd5e1", marginBottom: 6 }}>
            {issuedKey.api_key_notice}
          </p>
          <pre
            style={{
              background: "#0b1120",
              padding: 10,
              borderRadius: 8,
              fontSize: "0.75rem",
              overflowX: "auto",
              color: "#38bdf8",
            }}
          >{`API Key: ${issuedKey.api_key}

# Test Live Telemetry Packet:
curl -X POST ${API_BASE_URL}/api/v1/ingest \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${issuedKey.api_key}" \\
  -d '{"pm25": 28.4, "pm10": 46.0, "rh_pct": 82.0, "lat": ${issuedKey.sensor.lat}, "lon": ${issuedKey.sensor.lon}}'`}</pre>
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <div className="card-title">
            <span>
              <Radio size={13} /> My Registered Sensors ({mySensors.length})
            </span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Trust</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {mySensors.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.sensor_type}</td>
                  <td>{s.trust_weight}</td>
                  <td>{s.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-title">My Latest Immutable Readings ({myReadings.length})</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Raw PM2.5</th>
                <th>RH%</th>
                <th>GPS</th>
              </tr>
            </thead>
            <tbody>
              {myReadings.slice(0, 15).map((r) => (
                <tr key={r.id}>
                  <td>#{r.id}</td>
                  <td>{r.pm25_raw} µg/m³</td>
                  <td>{r.rh_pct}%</td>
                  <td>
                    {r.lat.toFixed(4)}, {r.lon.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
