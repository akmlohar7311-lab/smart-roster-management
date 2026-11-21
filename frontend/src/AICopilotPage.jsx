
import { apiFetch } from './lib/api'

import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import './AICopilotPage.css'

const suggestions = [
  {
    icon: '\u{1F4C5}',
    title: 'Roster Planning',
    question: 'How can I create a fair monthly employee roster?'
  },
  {
    icon: '\u26A0\uFE0F',
    title: 'Staffing Shortages',
    question: 'How should I handle understaffed shifts?'
  },
  {
    icon: '\u{1F334}',
    title: 'Leave Management',
    question: 'How can I prevent staffing conflicts when employees take leave?'
  },
  {
    icon: '\u{1F465}',
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

  // Scroll to newest message when conversation changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end'
    })
  }, [messages, loading])

  // Cancel unfinished requests if the page is closed.
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
      const response = await apiFetch('/api/ai/ask', {
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

      {/* Header */}

      <header className="ai-copilot-header">

        <div className="ai-header-identity">

          <div className="ai-logo">
            {'\u2726'}
          </div>

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
            {'\u21BB'} New Chat
          </button>

        </div>

      </header>

      {/* Chat Content */}

      <div className="ai-chat-content" ref={chatRef}>

        {showSuggestions && (

          <div className="ai-welcome">

            <div className="ai-welcome-icon">
              {'\u2726'}
            </div>

            <h2>
              How can I help you today?
            </h2>

            <p>
              Your AI assistant for smarter
              workforce planning, shift scheduling,
              and leave management.
            </p>

            {/* Suggestion Cards */}

            <div className="ai-suggestions">

              {suggestions.map(item => (

                <button
                  type="button"
                  key={item.title}
                  className="ai-suggestion-card"
                  disabled={loading}
                  onClick={() => sendMessage(item.question)}
                >

                  <span className="ai-suggestion-icon">
                    {item.icon}
                  </span>

                  <strong>
                    {item.title}
                  </strong>

                  <span className="ai-suggestion-arrow">
                    {'\u2192'}
                  </span>

                </button>

              ))}

            </div>

          </div>

        )}

        {/* Messages */}

        <div className="ai-messages">

          {messages.map(message => (

            <article
              key={message.id}
              className={`ai-message ai-message-${message.role}`}
            >

              <div className="ai-message-avatar">

                {message.role === 'assistant'
                  ? '\u2726'
                  : '\u{1F464}'}

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

          {/* Loading Animation */}

          {loading && (

            <div className="ai-message ai-message-assistant">

              <div className="ai-message-avatar">
                {'\u2726'}
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

      {/* Chat Footer */}

      <div className="ai-chat-footer">

        {error && (

          <div className="ai-error" role="alert">

            <span>
              {'\u26A0\uFE0F'} {error}
            </span>

            <button
              type="button"
              onClick={() => setError('')}
              aria-label="Dismiss error"
            >
              {'\u00D7'}
            </button>

          </div>

        )}

        {/* Message Input */}

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
            onChange={event => setInput(event.target.value)}
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
            {loading ? '...' : '\u27A4'}
          </button>

        </form>

        {/* Disclaimer */}

        <p className="ai-disclaimer">
          Enter to send {'\u00B7'} Shift+Enter for new line {'\u00B7'}
          Powered by Google Gemini {'\u00B7'}
          Read-only roster insights powered by Supabase and Google Gemini.
        </p>

      </div>

    </section>
  )
}

export default AICopilotPage
