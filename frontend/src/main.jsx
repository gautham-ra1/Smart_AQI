import React from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import App from "./App";
import "./assets/styles/global.css";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, color: "#fca5a5", background: "#0b1120", minHeight: "100vh", fontFamily: "monospace" }}>
          <h2>VayuMesh Frontend Error</h2>
          <pre style={{ marginTop: 12, whiteSpace: "pre-wrap" }}>
            {String(this.state.error?.stack || this.state.error)}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

// Note: Avoid React.StrictMode double-mount with react-leaflet MapContainer in dev
ReactDOM.createRoot(document.getElementById("root")).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
);
