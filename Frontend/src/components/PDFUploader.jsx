// =============================================================================
// PDFUploader.jsx — Handles drag-and-drop PDF uploads
// =============================================================================
//
// HOW FILE UPLOADS WORK:
//   1. User selects/drops a PDF file
//   2. We create a FormData object (like an HTML form submission)
//   3. We POST it to /api/upload using fetch()
//   4. The backend processes the PDF and responds with success/error
//   5. We notify the parent component (App.jsx) via onFileUploaded()
// =============================================================================

import { useState, useRef } from "react";

function PDFUploader({ apiBase, onFileUploaded }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [error, setError] = useState("");

  // Reference to the hidden file input element
  const fileInputRef = useRef(null);

  // ---------------------------------------------------------------------------
  // Drag and drop handlers
  // ---------------------------------------------------------------------------

  function handleDragOver(e) {
    e.preventDefault(); // IMPORTANT: prevent browser from opening the file
    setIsDragging(true);
  }

  function handleDragLeave() {
    setIsDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);

    // e.dataTransfer.files contains the dropped files
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      uploadFile(files[0]); // Only upload the first file
    }
  }

  // ---------------------------------------------------------------------------
  // File input change handler
  // ---------------------------------------------------------------------------
  function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  }

  // ---------------------------------------------------------------------------
  // Main upload function
  // ---------------------------------------------------------------------------
  async function uploadFile(file) {
    // Validate file type
    if (!file.name.endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }

    setError("");
    setIsUploading(true);
    setUploadProgress("Uploading file...");

    try {
      // FormData is the standard way to send files in HTTP requests
      // It creates a multipart/form-data encoded body
      const formData = new FormData();
      formData.append("file", file); // "file" matches the parameter name in FastAPI

      setUploadProgress("Processing PDF (extracting text, chunking, embedding)...");

      const response = await fetch(`${apiBase}/upload`, {
        method: "POST",
        body: formData,
        // DON'T set Content-Type header — fetch sets it automatically
        // with the correct multipart boundary when using FormData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      setUploadProgress(
        `✅ Done! Created ${data.details.chunks_created} chunks from ${data.details.characters_extracted.toLocaleString()} characters.`
      );

      // Notify parent component
      onFileUploaded(file.name);

      // Reset after 3 seconds
      setTimeout(() => {
        setUploadProgress("");
        setIsUploading(false);
      }, 3000);
    } catch (err) {
      setError(err.message);
      setIsUploading(false);
      setUploadProgress("");
    }

    // Reset the file input so the same file can be uploaded again if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="uploader">
      {/* Drag and Drop Zone */}
      <div
        className={`drop-zone ${isDragging ? "dragging" : ""} ${isUploading ? "uploading" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
      >
        {isUploading ? (
          <div className="upload-status">
            <div className="spinner"></div>
            <p>{uploadProgress}</p>
          </div>
        ) : (
          <>
            <div className="drop-icon">📤</div>
            <p className="drop-text">
              <strong>Drop PDF here</strong>
              <br />
              or click to browse
            </p>
          </>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="upload-error">
          ⚠️ {error}
        </div>
      )}

      {/* Hidden file input — triggered by clicking the drop zone */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: "none" }}
        onChange={handleFileSelect}
      />
    </div>
  );
}

export default PDFUploader;
