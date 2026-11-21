
import { useEffect, useRef, useState } from "react";
import "./AICopilotPage.css";

const SUGGESTIONS = [
  {
    icon: "📅",
    title: "Roster Planning",
    question: "What are the best practices for creating a fair monthly employee roster?",
  },
  {
    icon: "⚠️",
    title: "Staffing Shortages",
    question: "How should a manager handle understaffed shifts?",
  },
  {
    icon: "🌴",
    title: "Leave Management",
    question: "How can I manage employee leave without causing staffing conflicts?",
  },
  {
    icon: "👥",
    title: "Backup Planning",
    question: "How should I choose a backup employee for an uncovered shift?",
  },
];

const INITIAL_MESSAGE = {
  id: "welcome",
  role: "assistant",
  content:
    "Hello! I'm Datastraw AI Copilot. I can help you with employee scheduling, leave management, staffing shortages, and workforce planning. What would you like to know?",
  timestamp: new Date(),
};

function AICopilotPage() {
  const [messages, setMessages] = useState([
    INITIAL_MESSAGE,
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const requestControllerRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, loading]);

  useEffect(() => {
    return () => {
      requestControllerRef.current?.abort();
    };
  }, []);

  async function sendMessage(questionOverride) {
    const question = (
      questionOverride ?? input
    ).trim();

    if (loading || question.length < 3) {
      return;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };

    setMessages((previous) => [
      ...previous,
      userMessage,
    ]);

    setInput("");
    setError("");
    setLoading(true);

    const controller = new AbortController();
    requestControllerRef.current = controller;

    try {
      const response = await fetch("/api/ai/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
        }),
        signal: controller.signal,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to contact the AI service."
        );
      }

      if (!data.answer) {
        throw new Error(
          "The AI service returned an empty answer."
        );
      }

      const aiMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer,
        timestamp: new Date(),
      };

      setMessages((previous) => [
        ...previous,
        aiMessage,
      ]);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(
          err.message ||
            "Something went wrong. Please try again."
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }

      if (requestControllerRef.current === controller) {
        requestControllerRef.current = null;
      }
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage();
  }

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      sendMessage();
    }
  }

  function clearChat() {
    if (loading) {
      requestControllerRef.current?.abort();
      requestControllerRef.current = null;
      setLoading(false);
    }

    setMessages([
      {
        ...INITIAL_MESSAGE,
        timestamp: new Date(),
      },
    ]);

    setInput("");
    setError("");
    textareaRef.current?.focus();
  }

  const showSuggestions = messages.length === 1;

  return (
    <div className="ds-ai-page">
      <header className="ds-ai-header">
        <div className="ds-ai-header-left">
          <div className="ds-ai-logo">
            ✦
          </div>

          <div>
            <h1>AI Copilot</h1>
            <p>
              Your intelligent workforce assistant
            </p>
          </div>
        </div>

        <div className="ds-ai-header-actions">
          <span className="ds-ai-status">
            <span className="ds-ai-status-dot" />
            Gemini AI
          </span>

          <button
            type="button"
            className="ds-ai-clear-btn"
            onClick={clearChat}
          >
            ↻ New Chat
          </button>
        </div>
      </header>

      <section className="ds-ai-chat-area">
        {showSuggestions && (
          <div className="ds-ai-welcome">
            <div className="ds-ai-welcome-icon">
              ✦
            </div>

            <h2>
              How can I help you today?
            </h2>

            <p>
              Ask about scheduling, employee
              availability, staffing challenges,
              and workforce planning.
            </p>

            <div className="ds-ai-suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  type="button"
                  className="ds-ai-suggestion"
                  key={suggestion.title}
                  disabled={loading}
                  onClick={() =>
                    sendMessage(
                      suggestion.question
                    )
                  }
                >
                  <span className="ds-ai-suggestion-icon">
                    {suggestion.icon}
                  </span>

                  <span>
                    {suggestion.title}
                  </span>

                  <span className="ds-ai-suggestion-arrow">
                    ↗
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="ds-ai-messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`ds-ai-message ${
                message.role === "user"
                  ? "ds-ai-message-user"
                  : "ds-ai-message-assistant"
              }`}
            >
              <div className="ds-ai-avatar">
                {message.role === "assistant"
                  ? "✦"
                  : "👤"}
              </div>

              <div className="ds-ai-message-content">
                <div className="ds-ai-message-label">
                  {message.role === "assistant"
                    ? "Datastraw Copilot"
                    : "You"}
                </div>

                <div className="ds-ai-bubble">
                  {message.content}
                </div>

                <span className="ds-ai-message-time">
                  {new Date(
                    message.timestamp
                  ).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
          ))}

          {loading && (
            <div className="ds-ai-message ds-ai-message-assistant">
              <div className="ds-ai-avatar">
                ✦
              </div>

              <div className="ds-ai-message-content">
                <div className="ds-ai-message-label">
                  Datastraw Copilot
                </div>

                <div className="ds-ai-typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </section>

      <div className="ds-ai-bottom">
        {error && (
          <div
            className="ds-ai-error"
            role="alert"
          >
            <span>⚠ {error}</span>

            <button
              type="button"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        <form
          className="ds-ai-input-form"
          onSubmit={handleSubmit}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(event) =>
              setInput(event.target.value)
            }
            onKeyDown={handleKeyDown}
            placeholder="Ask Datastraw Copilot anything..."
            rows={2}
            maxLength={500}
            disabled={loading}
            aria-label="Message to AI Copilot"
          />

          <button
            type="submit"
            className="ds-ai-send-btn"
            disabled={
              loading ||
              input.trim().length < 3
            }
            aria-label="Send message"
          >
            {loading ? "…" : "➤"}
          </button>
        </form>

        <p className="ds-ai-disclaimer">
          Powered by Google Gemini ·
          AI suggestions should be reviewed
          before making scheduling decisions.
          Live roster data is not connected yet.
        </p>
      </div>
    </div>
  );
}

export default AICopilotPage;
