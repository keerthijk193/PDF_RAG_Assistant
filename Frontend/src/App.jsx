// // =============================================================================
// // App.jsx — The root component of our React application
// // =============================================================================
// //
// // WHAT IS REACT?
// // React is a JavaScript library for building user interfaces. Instead of
// // directly manipulating HTML (like old-school jQuery), React lets you describe
// // WHAT the UI should look like, and it handles the HOW.
// //
// // KEY CONCEPTS:
// //   - Component: A reusable UI piece (like a Lego block)
// //   - State:     Data that, when changed, causes the UI to re-render
// //   - Props:     Data passed from parent to child components
// //   - Hook:      Special functions (useState, useEffect) that add features
// // =============================================================================

// import { useState, useRef, useEffect } from "react";
// import ChatMessage from "./components/ChatMessage";
// import PDFUploader from "./components/PDFUploader";
// import ChatInput from "./components/ChatInput";
// import StatusBar from "./components/StatusBar";
// import "./App.css";

// // The URL of our FastAPI backend
// // In development: http://localhost:8000
// // Change this when deploying to production
// const API_BASE = "http://localhost:8000/api";

// function App() {
//   // ---------------------------------------------------------------------------
//   // STATE — React "state" variables cause the UI to re-render when they change
//   // ---------------------------------------------------------------------------

//   // messages: the full chat history displayed on screen
//   // Each message: { id, role: "user"|"assistant", content, sources? }
//   const [messages, setMessages] = useState([
//     {
//       id: "welcome",
//       role: "assistant",
//       content:
//         "👋 Hello! I'm your PDF AI Assistant. Upload a PDF document and I'll answer questions about it using AI.\n\nI use **RAG (Retrieval-Augmented Generation)** — I find the most relevant parts of your document and use them to give accurate, grounded answers.",
//     },
//   ]);

//   // isLoading: true while waiting for the AI to respond
//   const [isLoading, setIsLoading] = useState(false);

//   // uploadedFiles: list of PDF filenames that have been processed
//   const [uploadedFiles, setUploadedFiles] = useState([]);

//   // ollamaStatus: whether Ollama is running and which models are available
//   const [ollamaStatus, setOllamaStatus] = useState({
//     running: false,
//     models: [],
//   });

//   // selectedModel: which Ollama model to use for answering questions
//   const [selectedModel, setSelectedModel] = useState("llama3");

//   // ---------------------------------------------------------------------------
//   // REFS — for accessing DOM elements directly (not through React state)
//   // ---------------------------------------------------------------------------

//   // messagesEndRef: a reference to the bottom of the messages list
//   // We use it to auto-scroll to the latest message
//   const messagesEndRef = useRef(null);

//   // ---------------------------------------------------------------------------
//   // EFFECTS — code that runs when component mounts or state changes
//   // ---------------------------------------------------------------------------

//   // Check Ollama status when the app loads
//   useEffect(() => {
//     checkOllamaStatus();
//     checkUploadedFiles();
//   }, []); // Empty array [] = run once when component first mounts

//   // Auto-scroll to the bottom when new messages arrive
//   useEffect(() => {
//     messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
//   }, [messages]);

//   // ---------------------------------------------------------------------------
//   // FUNCTIONS
//   // ---------------------------------------------------------------------------

//   // NOTE: There is no dedicated /chat/status endpoint on the backend.
//   // We keep this function as a harmless placeholder instead of calling
//   // a URL that returns 404 (which was happening before).
//   async function checkOllamaStatus() {
//     // Intentionally does nothing right now — see note above.
//   }

//   async function checkUploadedFiles() {
//     try {
//       const response = await fetch(`${API_BASE}/status`);
//       if (response.ok) {
//         const data = await response.json();
//         setUploadedFiles(data.processed_files || []);
//       }
//     } catch (e) {
//       // Backend not running yet — that's okay
//     }
//   }

//   // Called by PDFUploader component when a file is successfully uploaded
//   function handleFileUploaded(filename) {
//     setUploadedFiles((prev) => [...prev, filename]);

//     // Add a system message to the chat
//     addMessage({
//       role: "assistant",
//       content: `✅ **"${filename}"** has been processed and added to the knowledge base!\n\nYou can now ask questions about this document.`,
//     });
//   }

//   // Adds a new message to the chat history
//   function addMessage(msg) {
//     const newMsg = {
//       id: Date.now().toString(),
//       ...msg,
//     };
//     setMessages((prev) => [...prev, newMsg]);
//     return newMsg.id;
//   }

//   // Called when the user sends a question
//   async function handleSendMessage(question) {
//     if (!question.trim() || isLoading) return;

//     // Add the user's message to the chat
//     addMessage({ role: "user", content: question });
//     setIsLoading(true);

//     // Create a placeholder for the AI's response
//     // We'll update this in real-time as tokens stream in
//     const assistantMsgId = Date.now().toString() + "-assistant";
//     setMessages((prev) => [
//       ...prev,
//       { id: assistantMsgId, role: "assistant", content: "", sources: [] },
//     ]);

//     try {
//       // Build the chat history to send (all messages except the welcome and the new empty one)
//       const historyToSend = messages
//         .filter((m) => m.id !== "welcome" && m.content !== "")
//         .map((m) => ({ role: m.role, content: m.content }));

//       // Call our FastAPI backend
//       // We use fetch() with a streaming reader to handle SSE responses
//       const response = await fetch(`${API_BASE}/chat`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({
//           question,
//           history: historyToSend,
//           model: selectedModel,
//         }),
//       });

//       if (!response.ok) {
//         throw new Error(`API error: ${response.statusText}`);
//       }

//       // Set up streaming reader
//       // ReadableStream allows us to read response data as it arrives
//       const reader = response.body.getReader();
//       const decoder = new TextDecoder(); // Converts bytes → text
//       let buffer = "";

//       // Read tokens as they arrive
//       while (true) {
//         const { done, value } = await reader.read();
//         if (done) break;

//         // Decode the chunk of bytes into text
//         buffer += decoder.decode(value, { stream: true });

//         // SSE format: each event is "data: {...}\n\n"
//         // Split by double newline to get individual events
//         const lines = buffer.split("\n\n");

//         // Process all complete events (keep the last incomplete one in buffer)
//         for (let i = 0; i < lines.length - 1; i++) {
//           const line = lines[i].trim();
//           if (!line.startsWith("data: ")) continue;

//           try {
//             const data = JSON.parse(line.slice(6)); // Remove "data: " prefix

//             if (data.type === "token") {
//               // Append the new token to the assistant's message
//               setMessages((prev) =>
//                 prev.map((msg) =>
//                   msg.id === assistantMsgId
//                     ? { ...msg, content: msg.content + data.content }
//                     : msg
//                 )
//               );
//             } else if (data.type === "sources") {
//               // Save the source chunks
//               setMessages((prev) =>
//                 prev.map((msg) =>
//                   msg.id === assistantMsgId
//                     ? { ...msg, sources: data.sources }
//                     : msg
//                 )
//               );
//             }
//           } catch (e) {
//             // Skip malformed JSON
//           }
//         }

//         buffer = lines[lines.length - 1]; // Keep incomplete event in buffer
//       }
//     } catch (error) {
//       // Log the full error to the browser console so it's easy to debug
//       // (Press F12 → Console tab to see this)
//       console.error("Chat request failed:", error);

//       // Show error message
//       // FIX: use the assistantMsgId we already created above, instead of
//       // calling Date.now() again (which would never match — it's a new
//       // timestamp every time it's called).
//       setMessages((prev) =>
//         prev.map((msg) =>
//           msg.id === assistantMsgId
//             ? {
//                 ...msg,
//                 content: `❌ Error: ${error.message}\n\nMake sure:\n1. The backend is running: \`uvicorn main:app --reload\`\n2. Ollama is running: \`ollama serve\`\n3. The model is downloaded: \`ollama pull ${selectedModel}\``,
//               }
//             : msg
//         )
//       );
//     } finally {
//       setIsLoading(false);
//     }
//   }

//   // ---------------------------------------------------------------------------
//   // RENDER — what gets displayed on screen
//   // ---------------------------------------------------------------------------
//   return (
//     <div className="app">
//       {/* Sidebar */}
//       <aside className="sidebar">
//         <div className="sidebar-header">
//           <div className="logo">
//             <span className="logo-icon">🧠</span>
//             <div>
//               <h1>PDF RAG Assistant</h1>
//               <p>Powered by Ollama + FAISS</p>
//             </div>
//           </div>
//         </div>

//         {/* PDF Upload Section */}
//         <div className="sidebar-section">
//           <h2 className="section-title">📄 Upload Documents</h2>
//           <PDFUploader
//             apiBase={API_BASE}
//             onFileUploaded={handleFileUploaded}
//           />
//         </div>

//         {/* Uploaded Files List */}
//         {uploadedFiles.length > 0 && (
//           <div className="sidebar-section">
//             <h2 className="section-title">📚 Knowledge Base</h2>
//             <ul className="file-list">
//               {uploadedFiles.map((file, i) => (
//                 <li key={i} className="file-item">
//                   <span className="file-icon">📄</span>
//                   <span className="file-name">{file}</span>
//                 </li>
//               ))}
//             </ul>
//           </div>
//         )}

//         {/* Model Selection */}
//         <div className="sidebar-section">
//           <h2 className="section-title">🤖 LLM Model</h2>
//           <select
//             className="model-select"
//             value={selectedModel}
//             onChange={(e) => setSelectedModel(e.target.value)}
//           >
//             <option value="llama3">Llama 3 (recommended)</option>
//             <option value="mistral">Mistral 7B</option>
//             <option value="llama2">Llama 2</option>
//             <option value="phi3">Phi-3 Mini (fast)</option>
//           </select>
//           <p className="model-hint">
//             Make sure to run: <code>ollama pull {selectedModel}</code>
//           </p>
//         </div>

//         <StatusBar uploadedFiles={uploadedFiles} />
//       </aside>

//       {/* Main Chat Area */}
//       <main className="chat-area">
//         <div className="messages-container">
//           {messages.map((msg) => (
//             <ChatMessage key={msg.id} message={msg} />
//           ))}

//           {/* Loading indicator */}
//           {isLoading && (
//             <div className="message assistant-message">
//               <div className="message-avatar">🤖</div>
//               <div className="message-bubble">
//                 <div className="typing-indicator">
//                   <span></span>
//                   <span></span>
//                   <span></span>
//                 </div>
//               </div>
//             </div>
//           )}

//           {/* Invisible element at the bottom for auto-scrolling */}
//           <div ref={messagesEndRef} />
//         </div>

//         {/* Input Area */}
//         <ChatInput
//           onSend={handleSendMessage}
//           isLoading={isLoading}
//           disabled={uploadedFiles.length === 0}
//           placeholder={
//             uploadedFiles.length === 0
//               ? "Upload a PDF first to start chatting..."
//               : "Ask a question about your documents..."
//           }
//         />
//       </main>
//     </div>
//   );
// }

// export default App;


// =============================================================================
// App.jsx — The root component of our React application
// =============================================================================
//
// WHAT IS REACT?
// React is a JavaScript library for building user interfaces. Instead of
// directly manipulating HTML (like old-school jQuery), React lets you describe
// WHAT the UI should look like, and it handles the HOW.
//
// KEY CONCEPTS:
//   - Component: A reusable UI piece (like a Lego block)
//   - State:     Data that, when changed, causes the UI to re-render
//   - Props:     Data passed from parent to child components
//   - Hook:      Special functions (useState, useEffect) that add features
// =============================================================================

import { useState, useRef, useEffect } from "react";
import ChatMessage from "./components/ChatMessage";
import PDFUploader from "./components/PDFUploader";
import ChatInput from "./components/ChatInput";
import StatusBar from "./components/StatusBar";
import "./App.css";

// The URL of our FastAPI backend.
//
// WHY import.meta.env.VITE_API_URL?
// This is Vite's way of reading environment variables at build time.
// - Locally: if no .env file exists, it falls back to localhost:8000
// - Deployed (Vercel): you'll set VITE_API_URL in Vercel's dashboard to
//   point at your Render backend URL, e.g. https://my-backend.onrender.com/api
// IMPORTANT: Vite only exposes variables that start with "VITE_" to the
// browser — this is a deliberate security feature so you don't accidentally
// leak server-only secrets into client-side JavaScript.
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

function App() {
  // ---------------------------------------------------------------------------
  // STATE — React "state" variables cause the UI to re-render when they change
  // ---------------------------------------------------------------------------

  // messages: the full chat history displayed on screen
  // Each message: { id, role: "user"|"assistant", content, sources? }
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content:
        "👋 Hello! I'm your PDF AI Assistant. Upload a PDF document and I'll answer questions about it using AI.\n\nI use **RAG (Retrieval-Augmented Generation)** — I find the most relevant parts of your document and use them to give accurate, grounded answers.",
    },
  ]);

  // isLoading: true while waiting for the AI to respond
  const [isLoading, setIsLoading] = useState(false);

  // uploadedFiles: list of PDF filenames that have been processed
  const [uploadedFiles, setUploadedFiles] = useState([]);

  // ollamaStatus: whether Ollama is running and which models are available
  const [ollamaStatus, setOllamaStatus] = useState({
    running: false,
    models: [],
  });

  // selectedModel: which Ollama model to use for answering questions
  const [selectedModel, setSelectedModel] = useState("llama-3.1-8b-instant");

  // ---------------------------------------------------------------------------
  // REFS — for accessing DOM elements directly (not through React state)
  // ---------------------------------------------------------------------------

  // messagesEndRef: a reference to the bottom of the messages list
  // We use it to auto-scroll to the latest message
  const messagesEndRef = useRef(null);

  // ---------------------------------------------------------------------------
  // EFFECTS — code that runs when component mounts or state changes
  // ---------------------------------------------------------------------------

  // Check Ollama status when the app loads
  useEffect(() => {
    checkOllamaStatus();
    checkUploadedFiles();
  }, []); // Empty array [] = run once when component first mounts

  // Auto-scroll to the bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ---------------------------------------------------------------------------
  // FUNCTIONS
  // ---------------------------------------------------------------------------

  // NOTE: There is no dedicated /chat/status endpoint on the backend.
  // We keep this function as a harmless placeholder instead of calling
  // a URL that returns 404 (which was happening before).
  async function checkOllamaStatus() {
    // Intentionally does nothing right now — see note above.
  }

  async function checkUploadedFiles() {
    try {
      const response = await fetch(`${API_BASE}/status`);
      if (response.ok) {
        const data = await response.json();
        setUploadedFiles(data.processed_files || []);
      }
    } catch (e) {
      // Backend not running yet — that's okay
    }
  }

  // Called by PDFUploader component when a file is successfully uploaded
  function handleFileUploaded(filename) {
    setUploadedFiles((prev) => [...prev, filename]);

    // Add a system message to the chat
    addMessage({
      role: "assistant",
      content: `✅ **"${filename}"** has been processed and added to the knowledge base!\n\nYou can now ask questions about this document.`,
    });
  }

  // Adds a new message to the chat history
  function addMessage(msg) {
    const newMsg = {
      id: Date.now().toString(),
      ...msg,
    };
    setMessages((prev) => [...prev, newMsg]);
    return newMsg.id;
  }

  // Called when the user sends a question
  async function handleSendMessage(question) {
    if (!question.trim() || isLoading) return;

    // Add the user's message to the chat
    addMessage({ role: "user", content: question });
    setIsLoading(true);

    // Create a placeholder for the AI's response
    // We'll update this in real-time as tokens stream in
    const assistantMsgId = Date.now().toString() + "-assistant";
    setMessages((prev) => [
      ...prev,
      { id: assistantMsgId, role: "assistant", content: "", sources: [] },
    ]);

    try {
      // Build the chat history to send (all messages except the welcome and the new empty one)
      const historyToSend = messages
        .filter((m) => m.id !== "welcome" && m.content !== "")
        .map((m) => ({ role: m.role, content: m.content }));

      // Call our FastAPI backend
      // We use fetch() with a streaming reader to handle SSE responses
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          history: historyToSend,
          model: selectedModel,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      // Set up streaming reader
      // ReadableStream allows us to read response data as it arrives
      const reader = response.body.getReader();
      const decoder = new TextDecoder(); // Converts bytes → text
      let buffer = "";

      // Read tokens as they arrive
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode the chunk of bytes into text
        buffer += decoder.decode(value, { stream: true });

        // SSE format: each event is "data: {...}\n\n"
        // Split by double newline to get individual events
        const lines = buffer.split("\n\n");

        // Process all complete events (keep the last incomplete one in buffer)
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (!line.startsWith("data: ")) continue;

          try {
            const data = JSON.parse(line.slice(6)); // Remove "data: " prefix

            if (data.type === "token") {
              // Append the new token to the assistant's message
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, content: msg.content + data.content }
                    : msg
                )
              );
            } else if (data.type === "sources") {
              // Save the source chunks
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, sources: data.sources }
                    : msg
                )
              );
            }
          } catch (e) {
            // Skip malformed JSON
          }
        }

        buffer = lines[lines.length - 1]; // Keep incomplete event in buffer
      }
    } catch (error) {
      // Log the full error to the browser console so it's easy to debug
      // (Press F12 → Console tab to see this)
      console.error("Chat request failed:", error);

      // Show error message
      // FIX: use the assistantMsgId we already created above, instead of
      // calling Date.now() again (which would never match — it's a new
      // timestamp every time it's called).
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: `❌ Error: ${error.message}\n\nMake sure:\n1. The backend is running: \`uvicorn main:app --reload\`\n2. Ollama is running: \`ollama serve\`\n3. The model is downloaded: \`ollama pull ${selectedModel}\``,
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  }

  // ---------------------------------------------------------------------------
  // RENDER — what gets displayed on screen
  // ---------------------------------------------------------------------------
  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <span className="logo-icon">🧠</span>
            <div>
              <h1>PDF RAG Assistant</h1>
              <p>Powered by Ollama + FAISS</p>
            </div>
          </div>
        </div>

        {/* PDF Upload Section */}
        <div className="sidebar-section">
          <h2 className="section-title">📄 Upload Documents</h2>
          <PDFUploader
            apiBase={API_BASE}
            onFileUploaded={handleFileUploaded}
          />
        </div>

        {/* Uploaded Files List */}
        {uploadedFiles.length > 0 && (
          <div className="sidebar-section">
            <h2 className="section-title">📚 Knowledge Base</h2>
            <ul className="file-list">
              {uploadedFiles.map((file, i) => (
                <li key={i} className="file-item">
                  <span className="file-icon">📄</span>
                  <span className="file-name">{file}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Model Selection */}
        <div className="sidebar-section">
          <h2 className="section-title">🤖 LLM Model</h2>
          <select
            className="model-select"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            <option value="llama-3.1-8b-instant">Llama 3.1 8B </option>
            <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
            <option value="openai/gpt-oss-20b">GPT OSS 20B</option>
            <option value="openai/gpt-oss-120b">GPT OSS 120B</option>
          </select>
          <p className="model-hint">
            Make sure to run: <code>ollama pull {selectedModel}</code>
          </p>
        </div>

        <StatusBar uploadedFiles={uploadedFiles} />
      </aside>

      {/* Main Chat Area */}
      <main className="chat-area">
        <div className="messages-container">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="message assistant-message">
              <div className="message-avatar">🤖</div>
              <div className="message-bubble">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          {/* Invisible element at the bottom for auto-scrolling */}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <ChatInput
          onSend={handleSendMessage}
          isLoading={isLoading}
          disabled={uploadedFiles.length === 0}
          placeholder={
            uploadedFiles.length === 0
              ? "Upload a PDF first to start chatting..."
              : "Ask a question about your documents..."
          }
        />
      </main>
    </div>
  );
}

export default App;