// =============================================================================
// ChatMessage.jsx — Renders a single chat message
// =============================================================================
// This component handles:
//   - User messages (right-aligned, dark background)
//   - Assistant messages (left-aligned, with markdown rendering)
//   - Source citations (collapsible snippets from the PDF)
// =============================================================================

import { useState } from "react";

// Simple markdown-to-HTML converter
// In a real app you'd use the "react-markdown" library
// But this shows you what's happening under the hood
function renderMarkdown(text) {
  if (!text) return "";

  return text
    // Bold: **text** → <strong>text</strong>
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    // Italic: *text* → <em>text</em>
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    // Inline code: `code` → <code>code</code>
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // Newlines → <br> tags
    .replace(/\n/g, "<br>");
}

function ChatMessage({ message }) {
  // State: whether the source snippets are expanded or collapsed
  const [sourcesExpanded, setSourcesExpanded] = useState(false);

  const isUser = message.role === "user";
  const hasSources = message.sources && message.sources.length > 0;

  return (
    <div className={`message ${isUser ? "user-message" : "assistant-message"}`}>
      {/* Avatar icon */}
      <div className="message-avatar">{isUser ? "👤" : "🤖"}</div>

      <div className="message-content">
        {/* Message bubble */}
        <div className="message-bubble">
          {isUser ? (
            // User messages: plain text
            <p>{message.content}</p>
          ) : (
            // Assistant messages: render markdown
            <div
              className="markdown-content"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />
          )}
        </div>

        {/* Source snippets — only shown for assistant messages */}
        {!isUser && hasSources && (
          <div className="sources-section">
            <button
              className="sources-toggle"
              onClick={() => setSourcesExpanded(!sourcesExpanded)}
            >
              📎 {sourcesExpanded ? "Hide" : "Show"} source snippets (
              {message.sources.length})
            </button>

            {sourcesExpanded && (
              <div className="sources-list">
                {message.sources.map((source, i) => (
                  <div key={i} className="source-chip">
                    <div className="source-label">Relevant excerpt {i + 1}</div>
                    <p className="source-text">
                      {/* Truncate long snippets */}
                      {source.length > 300 ? source.slice(0, 300) + "..." : source}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatMessage;
