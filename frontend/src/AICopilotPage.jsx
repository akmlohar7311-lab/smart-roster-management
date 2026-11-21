
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './AICopilotPage.css'

const suggestions = [
  {
    icon: '📅',
    title: 'Roster Planning',
    question: 'How can I create a fair monthly employee roster?'
  },
  {
    icon: '⚠️',
    title: 'Staffing Shortages',
    question: 'How should I handle understaffed shifts?'
  },
  {
    icon: '🌴',
    title: 'Leave Management',
    question: 'How can I prevent staffing conflicts when employees take leave?'
  },
  {
    icon: '👥',
    title: 'Backup Planning',
    question: 'How should I choose backup employees?'
  }
]

function createWelcomeMessage() {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content:
      "Hello! I'm **Datastraw AI Copilot**. I can help with roster planning, staffing shortages, employee leave, and workforce management.\n\nWhat would you like to know?",
    timestamp: new Date()
  }
}

function AICopilotPage() {
  const [messages, setMessages] = useState(
    () => [createWelcomeMessage()]
  )

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const chatRef = useRef(null)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const controllerRef = useRef(null)
  const busyRef = useRef(false)
  const requestIdRef = useRef(0)

  // Scroll to newest message when the conversation changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end'
    })
  }, [messages, loading])

  // Cancel an unfinished request if the page is closed.
  useEffect(() => {
    return () => controllerRef.current?.abort()
  }, [])

  async function sendMessage(questionOverride) {
    const question = (questionOverride ?? input).trim()

    if (busyRef.current || question.length < 3) {
      return
    }

    busyRef.current = true
    const requestId = ++requestIdRef.current

    setLoading(true)
    setError('')
    setInput('')

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      timestamp: new Date()
    }

    setMessages(previous => [
      ...previous,
      userMessage
    ])

    const controller = new AbortController()
    controllerRef.current = controller

    try {
      const response = await fetch('/api/ai/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question }),
        signal: controller.signal
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : `AI request failed (HTTP ${response.status})`
        )
      }

      if (!data.answer) {
        throw new Error(
          'Gemini returned an empty response.'
        )
      }

      if (requestId !== requestIdRef.current) {
        return
      }

      const aiMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer,
        timestamp: new Date()
      }

      setMessages(previous => [
        ...previous,
        aiMessage
      ])
    } catch (err) {
      if (
        err.name !== 'AbortError' &&
        requestId === requestIdRef.current
      ) {
        setError(
          err.message ||
          'Unable to connect to Gemini.'
        )
      }
    } finally {
      if (requestId === requestIdRef.current) {
        busyRef.current = false
        controllerRef.current = null
        setLoading(false)
      }
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    sendMessage()
  }

  function handleKeyDown(event) {
    if (
      event.key === 'Enter' &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault()
      sendMessage()
    }
  }

  function startNewChat() {
    ++requestIdRef.current
    controllerRef.current?.abort()
    controllerRef.current = null
    busyRef.current = false

    setMessages([createWelcomeMessage()])
    setInput('')
    setError('')
    setLoading(false)

    textareaRef.current?.focus()
  }

  function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const showSuggestions = messages.length === 1

  return (
    <section className="ai-copilot-page">

      <header className="ai-copilot-header">
        <div className="ai-header-identity">
          <div className="ai-logo">✦</div>

          <div>
            <h2>Datastraw AI Copilot</h2>
            <p>Intelligent Workforce Assistant</p>
          </div>
        </div>

        <div className="ai-header-actions">
          <span className="ai-model-label">
            <span className="ai-online-dot" />
            Powered by Gemini
          </span>

          <button
            type="button"
            className="ai-new-chat"
            onClick={startNewChat}
          >
            ↻ New Chat
          </button>
        </div>
      </header>

      <div className="ai-chat-content" ref={chatRef}>

        {showSuggestions && (
          <div className="ai-welcome">
            <div className="ai-welcome-icon">
              ✦
            </div>

            <h2>
              How can I help you today?
            </h2>

            <p>
              Your AI assistant for smarter
              workforce planning, shift scheduling,
              and leave management.
            </p>

            <div className="ai-suggestions">
              {suggestions.map(item => (
                <button
                  type="button"
                  key={item.title}
                  className="ai-suggestion-card"
                  disabled={loading}
                  onClick={() =>
                    sendMessage(item.question)
                  }
                >
                  <span className="ai-suggestion-icon">
                    {item.icon}
                  </span>

                  <strong>{item.title}</strong>

                  <span className="ai-suggestion-arrow">
                    ↗
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="ai-messages">

          {messages.map(message => (
            <article
              key={message.id}
              className={
                `ai-message ai-message-${message.role}`
              }
            >
              <div className="ai-message-avatar">
                {message.role === 'assistant'
                  ? '✦'
                  : '👤'}
              </div>

              <div className="ai-message-body">
                <div className="ai-message-topline">
                  <strong>
                    {message.role === 'assistant'
                      ? 'Datastraw Copilot'
                      : 'You'}
                  </strong>

                  <span>
                    {formatTime(message.timestamp)}
                  </span>
                </div>

                <div className="ai-message-bubble">
                  {message.role === 'assistant' ? (
                    <div className="ai-markdown">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        skipHtml
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="ai-user-text">
                      {message.content}
                    </div>
                  )}
                </div>
              </div>
            </article>
          ))}

          {loading && (
            <div className="ai-message ai-message-assistant">
              <div className="ai-message-avatar">
                ✦
              </div>

              <div className="ai-message-body">
                <div className="ai-message-topline">
                  <strong>Datastraw Copilot</strong>
                </div>

                <div
                  className="ai-typing"
                  aria-label="Gemini is responding"
                  role="status"
                >
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="ai-chat-footer">
        {error && (
          <div className="ai-error" role="alert">
            <span>⚠ {error}</span>
            <button
              type="button"
              onClick={() => setError('')}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        <form
          className="ai-input-area"
          onSubmit={handleSubmit}
        >
          <textarea
            ref={textareaRef}
            value={input}
            rows={2}
            maxLength={500}
            disabled={loading}
            aria-label="Message to AI Copilot"
            placeholder="Ask Datastraw AI Copilot anything..."
            onChange={event =>
              setInput(event.target.value)
            }
            onKeyDown={handleKeyDown}
          />

          <button
            type="submit"
            aria-label="Send message"
            disabled={
              loading ||
              input.trim().length < 3
            }
          >
            {loading ? '···' : '➤'}
          </button>
        </form>

        <p className="ai-disclaimer">
          Enter to send · Shift+Enter for new line ·
          Powered by Google Gemini ·
          Read-only roster insights powered by Supabase and Google Gemini.
        </p>
      </div>
    </section>
  )
}

export default AICopilotPage
