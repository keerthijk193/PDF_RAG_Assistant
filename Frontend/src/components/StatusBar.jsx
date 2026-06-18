// StatusBar.jsx — Shows system status at the bottom of the sidebar

function StatusBar({ uploadedFiles }) {
  return (
    <div className="status-bar">
      <div className="status-item">
        <span className={`status-dot ${uploadedFiles.length > 0 ? "green" : "yellow"}`}></span>
        <span>{uploadedFiles.length > 0 ? `${uploadedFiles.length} PDF(s) indexed` : "No PDFs uploaded"}</span>
      </div>
      <div className="status-item">
        <span className="status-dot green"></span>
        <span>FAISS vector store active</span>
      </div>
      <div className="status-item">
        <span className="status-dot orange"></span>
        <span>Ollama (check: ollama serve)</span>
      </div>
    </div>
  );
}

export default StatusBar;
