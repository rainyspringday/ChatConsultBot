import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import './App.css'

type Role = 'user' | 'assistant'

type ChatMessage = {
  id: string
  role: Role
  content: string
}

type AnalysisResult = {
  companyName: string
  currentState: string[]
  todoPlan: string[]
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

function ChatPage() {
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Hello. I am your business consulting assistant. Ask about strategy, operations, growth, or finance based on your uploaded documents.',
    },
  ])

  const canSubmit = useMemo(
    () => question.trim().length > 0 && !isLoading,
    [question, isLoading],
  )

  const submitQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const content = question.trim()
    if (!content || isLoading) return

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
    }

    setMessages((prev) => [...prev, userMessage])
    setQuestion('')
    setIsLoading(true)

    try {
      const response = await fetch(`${apiBase}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: content }),
      })

      if (!response.ok) {
        let detail = `Request failed (${response.status})`
        try {
          const err = (await response.json()) as { detail?: string }
          if (err.detail) detail = err.detail
        } catch {
          detail = `Request failed (${response.status})`
        }
        throw new Error(detail)
      }

      const data = (await response.json()) as { answer?: string }
      const answer = data.answer?.trim() || 'No answer returned.'

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: answer,
        },
      ])
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Could not reach the backend. Start your API service and try again.'
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: message,
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="page-grid">
      <header className="hero-card">
        <p className="eyebrow">Consulting Chat</p>
        <h1>Business Knowledge Assistant</h1>
        <p className="subtitle">
          Ask strategy, operations, growth, or finance questions and get
          document-grounded responses.
        </p>
      </header>

      <div className="stats-row">
        <article className="info-card">
          <p className="info-label">Model Endpoint</p>
          <p className="info-value">{apiBase}</p>
        </article>
        <article className="info-card">
          <p className="info-label">Mode</p>
          <p className="info-value">RAG Chat</p>
        </article>
        <article className="info-card">
          <p className="info-label">Messages</p>
          <p className="info-value">{messages.length}</p>
        </article>
      </div>

      <main className="chat-window" aria-live="polite">
        {messages.map((message) => (
          <article
            key={message.id}
            className={`message ${message.role === 'user' ? 'user' : 'assistant'}`}
          >
            <p>{message.content}</p>
          </article>
        ))}
        {isLoading && (
          <article className="message assistant">
            <p>Thinking...</p>
          </article>
        )}
      </main>

      <form className="composer" onSubmit={submitQuestion}>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a business question..."
          rows={3}
        />
        <button type="submit" disabled={!canSubmit}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </section>
  )
}

function AnalysisPage() {
  const [companyName, setCompanyName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [statusText, setStatusText] = useState(
    'Enter a company name to run a process analysis.',
  )

  const canSubmit = useMemo(
    () => companyName.trim().length > 1 && !isLoading,
    [companyName, isLoading],
  )

  const runAnalysis = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const name = companyName.trim()
    if (!name || isLoading) return
    setIsLoading(true)
    setStatusText('Requesting analysis from future API endpoint...')

    try {
      const response = await fetch(`${apiBase}/analyze-company`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ companyName: name }),
      })

      if (!response.ok) {
        let detail = `Request failed (${response.status})`
        try {
          const err = (await response.json()) as { detail?: string }
          if (err.detail) detail = err.detail
        } catch {
          detail = `Request failed (${response.status})`
        }
        throw new Error(detail)
      }

      const data = (await response.json()) as {
        companyName?: string
        currentState?: string[]
        todoPlan?: string[]
      }

      setResult({
        companyName: data.companyName ?? name,
        currentState: data.currentState ?? [],
        todoPlan: data.todoPlan ?? [],
      })
      setStatusText('Analysis loaded from API.')
    } catch {
      setResult({
        companyName: name,
        currentState: [
          'Data pipeline endpoint is not connected yet.',
          'Current report is a placeholder until backend release.',
          'Company-specific diagnostics will appear here after API launch.',
        ],
        todoPlan: [
          'Connect /analyze-company endpoint to backend service.',
          'Map CRM, finance, and operations data sources.',
          'Generate KPI baseline and risk map.',
          'Prioritize 30/60/90-day improvement actions.',
        ],
      })
      setStatusText(
        'API endpoint is not available yet. Showing preview structure.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="page-grid">
      <header className="hero-card">
        <p className="eyebrow">Company Analysis</p>
        <h1>Business Process Snapshot</h1>
        <p className="subtitle">
          Submit company name, call a future API endpoint, and review a practical
          TODO roadmap.
        </p>
      </header>

      <form className="analysis-form" onSubmit={runAnalysis}>
        <label htmlFor="companyName">Company Name</label>
        <input
          id="companyName"
          value={companyName}
          onChange={(event) => setCompanyName(event.target.value)}
          placeholder="Example: Northstar Logistics"
        />
        <button type="submit" disabled={!canSubmit}>
          {isLoading ? 'Analyzing...' : 'Analyze'}
        </button>
      </form>

      <section className="result-card">
        <p className="status-text">{statusText}</p>
        {result && (
          <div className="analysis-grid">
            <article className="panel">
              <h2>{result.companyName}</h2>
              <h3>Current State</h3>
              <ul>
                {result.currentState.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
            <article className="panel">
              <h3>Future Advice (TODO Plan)</h3>
              <ol>
                {result.todoPlan.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            </article>
          </div>
        )}
      </section>
    </section>
  )
}

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <p className="brand">ChatConsultBot</p>
        <nav>
          <NavLink to="/" end className="nav-link">
            Assistant Chat
          </NavLink>
          <NavLink to="/analysis" className="nav-link">
            Company Analysis
          </NavLink>
        </nav>
      </aside>
      <div className="main-content">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
        </Routes>
      </div>
    </div>
  )
}

export default App
