// =============================================================================
// ChatInput.jsx — The text input bar at the bottom of the chat
// =============================================================================

import { useState, useRef } from "react";

function ChatInput({ onSend, isLoading, disabled, placeholder }) {
  const [inputText, setInputText] = useState("");
  const textareaRef = useRef(null);

  function handleSend() {
    if (!inputText.trim() || isLoading || disabled) return;
    onSend(inputText.trim());
    setInputText("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e) {
    // Send on Enter (but not Shift+Enter, which adds a newline)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleInput(e) {
    setInputText(e.target.value);
    // Auto-resize textarea as user types
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px";
    }
  }

  return (
    <div className="chat-input-area">
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input"
          value={inputText}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={!inputText.trim() || isLoading || disabled}
          title="Send (Enter)"
        >
          {isLoading ? "⏳" : "➤"}
        </button>
      </div>
      <p className="input-hint">Press Enter to send · Shift+Enter for new line</p>
    </div>
  );
}

export default ChatInput;
