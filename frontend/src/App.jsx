import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/common/Navbar";
import PublicHeatmap from "./modules/public/PublicHeatmap";
import HealthAdvisory from "./modules/public/HealthAdvisory";
import AQIHistory from "./modules/public/AQIHistory";
import CitizenDashboard from "./modules/citizen/CitizenDashboard";
import AdminDashboard from "./modules/admin/AdminDashboard";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="app-shell">
          <Navbar />
          <Routes>
            <Route path="/" element={<PublicHeatmap />} />
            <Route path="/advisory" element={<HealthAdvisory />} />
            <Route path="/history" element={<AQIHistory />} />
            <Route path="/citizen" element={<CitizenDashboard />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
