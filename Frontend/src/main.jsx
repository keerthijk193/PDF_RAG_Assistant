// =============================================================================
// main.jsx — The entry point for the React application
// =============================================================================
// This is the FIRST file that runs when the browser loads the app.
// It "mounts" the React app into the #root <div> in index.html.
// =============================================================================

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// ReactDOM.createRoot() creates the root of our React component tree
// document.getElementById("root") finds the <div id="root"> in index.html
const root = ReactDOM.createRoot(document.getElementById("root"));

// root.render() renders our <App /> component into that div
root.render(
  // StrictMode helps catch bugs by running components twice in development
  // (it's removed automatically in production builds)
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
