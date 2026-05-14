import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import './App.css'

type ChatSession = { id: number; title: string; createdAt: string }
type ChatMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  rating?: number | null
  createdAt: string
}
type RevenuePoint = { year: number; revenue: number; expectedRevenue: number }
type AnalysisResult = {
  id?: number
  companyName: string
  currentState: string[]
  todoPlan: string[]
  benchmarkCompany?: string
  maturityScore?: number
  focusTopics?: string[]
  revenueSeries?: RevenuePoint[]
  userRating?: number | null
  createdAt?: string
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const authTokenKey = 'chatconsultbot_auth_token'
const usernameKey = 'chatconsultbot_username'

type AuthData = {
  token: string
  username: string
}

function getStoredAuth(): AuthData | null {
  const token = localStorage.getItem(authTokenKey)
  const username = localStorage.getItem(usernameKey)
  if (!token || !username) return null
  return { token, username }
}

function storeAuth(auth: AuthData) {
  localStorage.setItem(authTokenKey, auth.token)
  localStorage.setItem(usernameKey, auth.username)
}

function clearAuth() {
  localStorage.removeItem(authTokenKey)
  localStorage.removeItem(usernameKey)
}

function buildAuthHeaders(token: string) {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }
}

function renderInlineFormatting(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={`strong-${index}`}>{part.slice(2, -2)}</strong>
    }
    return <Fragment key={`text-${index}`}>{part}</Fragment>
  })
}

function MessageContent({ content }: { content: string }) {
  const lines = content.split('\n')
  const items: Array<
    | { type: 'p'; text: string }
    | { type: 'ul'; items: string[] }
    | { type: 'ol'; items: string[] }
  > = []

  let index = 0
  while (index < lines.length) {
    const raw = lines[index]
    const trimmed = raw.trim()

    if (!trimmed) {
      index += 1
      continue
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const listItems: string[] = []
      while (index < lines.length) {
        const current = lines[index].trim()
        if (current.startsWith('- ') || current.startsWith('* ')) {
          listItems.push(current.slice(2).trim())
          index += 1
        } else {
          break
        }
      }
      items.push({ type: 'ul', items: listItems })
      continue
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const listItems: string[] = []
      while (index < lines.length) {
        const current = lines[index].trim()
        if (/^\d+\.\s+/.test(current)) {
          listItems.push(current.replace(/^\d+\.\s+/, '').trim())
          index += 1
        } else {
          break
        }
      }
      items.push({ type: 'ol', items: listItems })
      continue
    }

    items.push({ type: 'p', text: trimmed })
    index += 1
  }

  if (items.length === 0) {
    return <p>{content}</p>
  }

  return (
    <>
      {items.map((item, itemIndex) => {
        if (item.type === 'ul') {
          return (
            <ul key={`ul-${itemIndex}`} className="message-list">
              {item.items.map((listItem, listIndex) => (
                <li key={`ul-item-${itemIndex}-${listIndex}`}>
                  {renderInlineFormatting(listItem)}
                </li>
              ))}
            </ul>
          )
        }

        if (item.type === 'ol') {
          return (
            <ol key={`ol-${itemIndex}`} className="message-list">
              {item.items.map((listItem, listIndex) => (
                <li key={`ol-item-${itemIndex}-${listIndex}`}>
                  {renderInlineFormatting(listItem)}
                </li>
              ))}
            </ol>
          )
        }

        return <p key={`p-${itemIndex}`}>{renderInlineFormatting(item.text)}</p>
      })}
    </>
  )
}

function normalizeAnalysisText(text: string): string {
  return text
    .replace(/^\s*[-*•]\s*/, '')
    .replace(/^\s*\d+[\.\)]\s*/, '')
    .replace(/\*\*/g, '')
    .trim()
}

function AnalysisItem({ text }: { text: string }) {
  const cleaned = normalizeAnalysisText(text)
  return <>{renderInlineFormatting(cleaned)}</>
}

type TopicStat = { label: string; score: number }

function buildTopicStats(currentState: string[], todoPlan: string[]): TopicStat[] {
  const buckets = [
    { label: 'Operations', keywords: ['operation', 'process', 'workflow', 'execution'] },
    { label: 'Finance', keywords: ['finance', 'financial', 'cost', 'revenue', 'profit'] },
    { label: 'Market', keywords: ['market', 'customer', 'demand', 'competition', 'sales'] },
    { label: 'Risk', keywords: ['risk', 'compliance', 'security', 'issue', 'challenge'] },
    { label: 'Growth', keywords: ['growth', 'strategy', 'initiative', 'innovation', 'scale'] },
  ]

  const combined = [...currentState, ...todoPlan].map((item) =>
    normalizeAnalysisText(item).toLowerCase(),
  )

  return buckets.map((bucket) => {
    const score = combined.reduce((acc, text) => {
      const hit = bucket.keywords.some((keyword) => text.includes(keyword))
      return acc + (hit ? 1 : 0)
    }, 0)
    return { label: bucket.label, score }
  })
}

function formatRevenue(value: number): string {
  if (!Number.isFinite(value)) return '-'
  if (Math.abs(value) >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(1)}T`
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  return value.toFixed(0)
}

function RevenueChart({ series }: { series: RevenuePoint[] }) {
  if (!series.length) return null

  const sorted = [...series].sort((a, b) => a.year - b.year)
  const width = 720
  const height = 230
  const pad = 26
  const maxY = Math.max(...sorted.map((point) => Math.max(point.revenue, point.expectedRevenue)))
  const minY = Math.min(...sorted.map((point) => Math.min(point.revenue, point.expectedRevenue)))
  const range = Math.max(1, maxY - minY)

  const toX = (index: number) =>
    pad + (index * (width - pad * 2)) / Math.max(1, sorted.length - 1)
  const toY = (value: number) => height - pad - ((value - minY) / range) * (height - pad * 2)

  const actual = sorted.map((point, index) => `${toX(index)},${toY(point.revenue)}`).join(' ')
  const expected = sorted
    .map((point, index) => `${toX(index)},${toY(point.expectedRevenue)}`)
    .join(' ')

  return (
    <div className="revenue-chart">
      <div className="chart-legend">
        <span className="legend-item actual">Revenue</span>
        <span className="legend-item expected">Expected revenue</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Revenue trend chart">
        <polyline points={expected} className="line-expected" />
        <polyline points={actual} className="line-actual" />
        {sorted.map((point, index) => (
          <g key={point.year}>
            <circle cx={toX(index)} cy={toY(point.revenue)} r="3.3" className="dot-actual" />
            <text x={toX(index)} y={height - 6} className="chart-year">
              {point.year}
            </text>
          </g>
        ))}
      </svg>
      <div className="chart-summary">
        <span>Latest revenue: {formatRevenue(sorted[sorted.length - 1].revenue)}</span>
        <span>Target: {formatRevenue(sorted[sorted.length - 1].expectedRevenue)}</span>
      </div>
    </div>
  )
}

function GrowthBars({ series }: { series: RevenuePoint[] }) {
  if (series.length < 2) return null
  const sorted = [...series].sort((a, b) => a.year - b.year)
  const growth = sorted.slice(1).map((point, idx) => {
    const prev = sorted[idx]
    const actual = ((point.revenue - prev.revenue) / Math.max(1, prev.revenue)) * 100
    const expected =
      ((point.expectedRevenue - prev.expectedRevenue) / Math.max(1, prev.expectedRevenue)) *
      100
    return { year: point.year, actual, expected }
  })
  const maxVal = Math.max(1, ...growth.map((g) => Math.max(g.actual, g.expected)))

  return (
    <div className="growth-bars">
      {growth.map((item) => (
        <div key={item.year} className="growth-row">
          <span className="growth-year">{item.year}</span>
          <div className="growth-track">
            <div
              className="growth-fill actual"
              style={{ width: `${Math.max(0, (item.actual / maxVal) * 100)}%` }}
            />
          </div>
          <div className="growth-track">
            <div
              className="growth-fill expected"
              style={{ width: `${Math.max(0, (item.expected / maxVal) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

function RevenueGapChart({ series }: { series: RevenuePoint[] }) {
  if (!series.length) return null
  const sorted = [...series].sort((a, b) => a.year - b.year)
  const gaps = sorted.map((point) => ({
    year: point.year,
    gap: Math.max(0, point.expectedRevenue - point.revenue),
  }))
  const maxGap = Math.max(1, ...gaps.map((g) => g.gap))

  return (
    <div className="gap-bars">
      {gaps.map((item) => (
        <div key={item.year} className="gap-row">
          <span>{item.year}</span>
          <div className="gap-track">
            <div className="gap-fill" style={{ width: `${(item.gap / maxGap) * 100}%` }} />
          </div>
          <strong>{formatRevenue(item.gap)}</strong>
        </div>
      ))}
    </div>
  )
}

function LoginPage({ onLogin }: { onLogin: (auth: AuthData) => void }) {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const canSubmit = useMemo(
    () => username.trim().length >= 3 && password.length >= 6 && !isLoading,
    [username, password, isLoading],
  )

  const submitLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canSubmit) return
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      })
      const data = (await response.json()) as {
        detail?: string
        access_token?: string
        username?: string
      }

      if (!response.ok || !data.access_token || !data.username) {
        throw new Error(data.detail ?? `Login failed (${response.status})`)
      }

      onLogin({ token: data.access_token, username: data.username })
      navigate('/')
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="auth-shell">
      <form className="auth-card" onSubmit={submitLogin}>
        <p className="eyebrow">Welcome Back</p>
        <h1>Sign In</h1>
        <label htmlFor="login-username">Username</label>
        <input
          id="login-username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          placeholder="your username"
        />
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          placeholder="min. 6 characters"
        />
        {error && <p className="auth-error">{error}</p>}
        <button type="submit" disabled={!canSubmit}>
          {isLoading ? 'Signing in...' : 'Sign in'}
        </button>
        <p className="auth-footnote">
          Need an account? <NavLink to="/register">Create one</NavLink>
        </p>
      </form>
    </section>
  )
}

function RegisterPage({ onLogin }: { onLogin: (auth: AuthData) => void }) {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const canSubmit = useMemo(
    () =>
      username.trim().length >= 3 &&
      password.length >= 6 &&
      confirmPassword === password &&
      !isLoading,
    [username, password, confirmPassword, isLoading],
  )

  const submitRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canSubmit) return
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${apiBase}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      })
      const data = (await response.json()) as {
        detail?: string
        access_token?: string
        username?: string
      }

      if (!response.ok || !data.access_token || !data.username) {
        throw new Error(data.detail ?? `Registration failed (${response.status})`)
      }

      onLogin({ token: data.access_token, username: data.username })
      navigate('/')
    } catch (errorValue) {
      setError(
        errorValue instanceof Error ? errorValue.message : 'Registration failed',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="auth-shell">
      <form className="auth-card" onSubmit={submitRegister}>
        <p className="eyebrow">New Account</p>
        <h1>Register</h1>
        <label htmlFor="register-username">Username</label>
        <input
          id="register-username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          placeholder="choose a username"
        />
        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="new-password"
          placeholder="min. 6 characters"
        />
        <label htmlFor="register-confirm-password">Confirm Password</label>
        <input
          id="register-confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          autoComplete="new-password"
          placeholder="repeat password"
        />
        {confirmPassword && confirmPassword !== password && (
          <p className="auth-error">Passwords do not match.</p>
        )}
        {error && <p className="auth-error">{error}</p>}
        <button type="submit" disabled={!canSubmit}>
          {isLoading ? 'Creating account...' : 'Create account'}
        </button>
        <p className="auth-footnote">
          Already registered? <NavLink to="/login">Sign in</NavLink>
        </p>
      </form>
    </section>
  )
}

function ChatPage({
  token,
  activeChatId,
  onEnsureChat,
  onRefreshChats,
}: {
  token: string
  activeChatId: number | null
  onEnsureChat: () => Promise<number | null>
  onRefreshChats: () => Promise<void>
}) {
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null)
  const [messageRatings, setMessageRatings] = useState<Record<number, number>>({})
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const activeRequestRef = useRef<AbortController | null>(null)
  const streamingTimerRef = useRef<number | null>(null)
  const maxComposerHeight = 140

  const canSubmit = useMemo(
    () => question.trim().length > 0 && !isLoading,
    [question, isLoading],
  )

  useEffect(() => {
    const loadMessages = async () => {
      if (!activeChatId) {
        setMessages([])
        return
      }
      if (isLoading) return
      const response = await fetch(`${apiBase}/chats/${activeChatId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) {
        setMessages([])
        return
      }
      const data = (await response.json()) as ChatMessage[]
      setMessages(data)
      setMessageRatings(
        Object.fromEntries(
          data
            .filter((item) => item.role === 'assistant' && typeof item.rating === 'number')
            .map((item) => [item.id, Number(item.rating)]),
        ),
      )
    }
    loadMessages()
  }, [activeChatId, token, isLoading])

  const copyMessage = async (messageId: number, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedMessageId(messageId)
      window.setTimeout(() => setCopiedMessageId((prev) => (prev === messageId ? null : prev)), 1200)
    } catch {
      setCopiedMessageId(null)
    }
  }

  const rateMessage = async (messageId: number, rating: -1 | 1) => {
    if (!activeChatId) return
    const response = await fetch(`${apiBase}/chats/${activeChatId}/messages/${messageId}/feedback`, {
      method: 'POST',
      headers: buildAuthHeaders(token),
      body: JSON.stringify({ rating }),
    })
    if (!response.ok) return
    setMessageRatings((prev) => ({ ...prev, [messageId]: rating }))
  }

  useEffect(() => {
    return () => {
      activeRequestRef.current?.abort()
      if (streamingTimerRef.current !== null) {
        window.clearInterval(streamingTimerRef.current)
      }
    }
  }, [])

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    const nextHeight = Math.min(textarea.scrollHeight, maxComposerHeight)
    textarea.style.height = `${nextHeight}px`
    textarea.style.overflowY = textarea.scrollHeight > maxComposerHeight ? 'auto' : 'hidden'
  }, [question])

  const submitQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const content = question.trim()
    if (!content || isLoading) return
    setIsLoading(true)

    let targetChatId = activeChatId
    if (!targetChatId) {
      targetChatId = await onEnsureChat()
    }
    if (!targetChatId) {
      setIsLoading(false)
      return
    }

    const optimisticUserMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, optimisticUserMessage])
    setQuestion('')

    try {
      activeRequestRef.current?.abort()
      const controller = new AbortController()
      activeRequestRef.current = controller
      const response = await fetch(`${apiBase}/chats/${targetChatId}/messages`, {
        method: 'POST',
        headers: buildAuthHeaders(token),
        body: JSON.stringify({ question: content }),
        signal: controller.signal,
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
        answer?: string
        chatTitle?: string
        messageId?: number
      }
      const answer = data.answer?.trim() || 'No answer returned.'
      const assistantId = data.messageId ?? Date.now() + 1
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          rating: null,
          createdAt: new Date().toISOString(),
        },
      ])
      if (streamingTimerRef.current !== null) {
        window.clearInterval(streamingTimerRef.current)
      }
      let cursor = 0
      const step = 12
      streamingTimerRef.current = window.setInterval(() => {
        cursor = Math.min(cursor + step, answer.length)
        const next = answer.slice(0, cursor)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: next,
                }
              : msg,
          ),
        )
        if (cursor >= answer.length && streamingTimerRef.current !== null) {
          window.clearInterval(streamingTimerRef.current)
          streamingTimerRef.current = null
        }
      }, 22)
      await onRefreshChats()
      const syncResponse = await fetch(`${apiBase}/chats/${targetChatId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (syncResponse.ok) {
        const synced = (await syncResponse.json()) as ChatMessage[]
        setMessages(synced)
        setMessageRatings(
          Object.fromEntries(
            synced
              .filter((item) => item.role === 'assistant' && typeof item.rating === 'number')
              .map((item) => [item.id, Number(item.rating)]),
          ),
        )
      }
    } catch (error) {
      const message =
        error instanceof DOMException && error.name === 'AbortError'
          ? 'Request was cancelled.'
          : error instanceof Error
          ? error.message
          : 'Could not reach the backend. Start your API service and try again.'
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          role: 'assistant',
          content: message,
          createdAt: new Date().toISOString(),
        },
      ])
    } finally {
      activeRequestRef.current = null
      setIsLoading(false)
    }
  }

  return (
    <section className="chat-layout">
      <main className="chat-window" aria-live="polite">
        <div className="chat-content">
          {messages.length === 0 && !isLoading && (
            <div className="chat-empty-state">
              <h2>What can I help with today?</h2>
              <p>Start with a question, idea, or task.</p>
            </div>
          )}
          {messages.map((message) => (
            <article
              key={message.id}
              className={`message ${message.role === 'user' ? 'user' : 'assistant'}`}
            >
              <MessageContent content={message.content} />
              {message.role === 'assistant' && message.content.trim() && (
                <div className="message-actions">
                  <button
                    type="button"
                    className="message-action-btn"
                    onClick={() => {
                      void copyMessage(message.id, message.content)
                    }}
                  >
                    {copiedMessageId === message.id ? 'Copied' : 'Copy'}
                  </button>
                  <button
                    type="button"
                    className={`message-action-btn ${messageRatings[message.id] === 1 ? 'active' : ''}`}
                    onClick={() => {
                      void rateMessage(message.id, 1)
                    }}
                  >
                    👍
                  </button>
                  <button
                    type="button"
                    className={`message-action-btn ${messageRatings[message.id] === -1 ? 'active' : ''}`}
                    onClick={() => {
                      void rateMessage(message.id, -1)
                    }}
                  >
                    👎
                  </button>
                </div>
              )}
            </article>
          ))}
          {isLoading && (
            <article className="message assistant">
              <p>Thinking...</p>
            </article>
          )}
          </div>
      </main>

      <form className="composer" onSubmit={submitQuestion}>
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(event) => {
            setQuestion(event.target.value)
          }}
          placeholder="Ask anything..."
          rows={1}
        />
        <button type="submit" disabled={!canSubmit}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </section>
  )
}

function AnalysisPage({ token }: { token: string }) {
  const [companyName, setCompanyName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [history, setHistory] = useState<AnalysisResult[]>([])
  const [visibleStateCount, setVisibleStateCount] = useState(0)
  const [visibleTodoCount, setVisibleTodoCount] = useState(0)
  const [statusText, setStatusText] = useState(
    'Enter a company name to run a process analysis.',
  )
  const analysisRequestRef = useRef<AbortController | null>(null)
  const revealTimerRef = useRef<number | null>(null)
  const topicStats = useMemo(
    () => (result ? buildTopicStats(result.currentState, result.todoPlan) : []),
    [result],
  )
  const maxTopicScore = useMemo(
    () => Math.max(1, ...topicStats.map((item) => item.score)),
    [topicStats],
  )

  const canSubmit = useMemo(
    () => companyName.trim().length > 1 && !isLoading,
    [companyName, isLoading],
  )

  const loadHistory = useCallback(async () => {
    const response = await fetch(`${apiBase}/company-analyses`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) return
    const data = (await response.json()) as AnalysisResult[]
    setHistory(data)
  }, [token])

  useEffect(() => {
    const run = async () => {
      await loadHistory()
    }
    run()
  }, [loadHistory])

  useEffect(() => {
    setVisibleStateCount(0)
    setVisibleTodoCount(0)
    if (!result) return
    if (revealTimerRef.current !== null) {
      window.clearInterval(revealTimerRef.current)
    }
    let stateCursor = 0
    let todoCursor = 0
    revealTimerRef.current = window.setInterval(() => {
      stateCursor = Math.min(stateCursor + 1, result.currentState.length)
      todoCursor = Math.min(todoCursor + 1, result.todoPlan.length)
      setVisibleStateCount(stateCursor)
      setVisibleTodoCount(todoCursor)
      if (
        stateCursor >= result.currentState.length &&
        todoCursor >= result.todoPlan.length &&
        revealTimerRef.current !== null
      ) {
        window.clearInterval(revealTimerRef.current)
        revealTimerRef.current = null
      }
    }, 110)
    return () => {
      if (revealTimerRef.current !== null) {
        window.clearInterval(revealTimerRef.current)
      }
    }
  }, [result])

  useEffect(() => {
    return () => {
      analysisRequestRef.current?.abort()
      if (revealTimerRef.current !== null) {
        window.clearInterval(revealTimerRef.current)
      }
    }
  }, [])

  const runAnalysis = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const name = companyName.trim()
    if (!name || isLoading) return
    setIsLoading(true)
    setStatusText('Requesting analysis from future API endpoint...')

    try {
      analysisRequestRef.current?.abort()
      const controller = new AbortController()
      analysisRequestRef.current = controller
      const response = await fetch(`${apiBase}/analyze-company`, {
        method: 'POST',
        headers: buildAuthHeaders(token),
        body: JSON.stringify({ companyName: name }),
        signal: controller.signal,
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
        id?: number
        companyName?: string
        currentState?: string[]
        todoPlan?: string[]
        benchmarkCompany?: string
        maturityScore?: number
        focusTopics?: string[]
        revenueSeries?: RevenuePoint[]
        userRating?: number | null
        createdAt?: string
      }

      setResult({
        id: data.id,
        companyName: data.companyName ?? name,
        currentState: data.currentState ?? [],
        todoPlan: data.todoPlan ?? [],
        benchmarkCompany: data.benchmarkCompany,
        maturityScore: data.maturityScore,
        focusTopics: data.focusTopics ?? [],
        revenueSeries: data.revenueSeries ?? [],
        userRating: data.userRating ?? null,
        createdAt: data.createdAt,
      })
      setStatusText('Analysis loaded from API.')
      loadHistory()
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }
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
        benchmarkCompany: 'Microsoft',
        maturityScore: undefined,
        focusTopics: [],
        revenueSeries: [],
        userRating: null,
      })
      setStatusText(
        'API endpoint is not available yet. Showing preview structure.',
      )
    } finally {
      analysisRequestRef.current = null
      setIsLoading(false)
    }
  }

  const deleteAnalysis = async (analysisId?: number) => {
    const normalizedId = Number(analysisId)
    if (!Number.isFinite(normalizedId) || normalizedId <= 0) return

    const response = await fetch(`${apiBase}/company-analyses/${normalizedId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
      setStatusText('Could not delete analysis. Please try again.')
      return
    }

    setHistory((prev) => prev.filter((item) => Number(item.id) !== normalizedId))
    setResult((prev) => (Number(prev?.id) === normalizedId ? null : prev))
    if (Number(result?.id) === normalizedId) {
      setStatusText('Analysis deleted.')
    }
    await loadHistory()
  }

  const rateAnalysis = async (analysisId: number | undefined, rating: number) => {
    const normalizedId = Number(analysisId)
    if (!Number.isFinite(normalizedId) || normalizedId <= 0) return
    const response = await fetch(`${apiBase}/company-analyses/${normalizedId}/rating`, {
      method: 'POST',
      headers: buildAuthHeaders(token),
      body: JSON.stringify({ rating }),
    })
    if (!response.ok) return
    setResult((prev) =>
      prev?.id === normalizedId
        ? {
            ...prev,
            userRating: rating,
          }
        : prev,
    )
    setHistory((prev) =>
      prev.map((item) =>
        item.id === normalizedId
          ? {
              ...item,
              userRating: rating,
            }
          : item,
      ),
    )
  }

  return (
    <section className="page-grid analysis-page">
      <header className="hero-card compact">
        <p className="eyebrow">Company Analysis</p>
        <h1>Business Process Snapshot</h1>
        <p className="subtitle">Analyze multiple companies and keep saved history.</p>
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
          <div className="analysis-sections">
            <article className="panel analysis-meta-panel">
              <div className="analysis-meta-row">
                <span className="meta-label">Benchmark</span>
                <strong>{result.benchmarkCompany ?? 'Microsoft'}</strong>
              </div>
              <div className="analysis-meta-row">
                <span className="meta-label">Maturity score</span>
                <strong>{result.maturityScore ?? '-'}</strong>
              </div>
              {!!result.focusTopics?.length && (
                <div className="topic-chip-row">
                  {result.focusTopics.map((topic) => (
                    <span key={topic} className="topic-chip">
                      {topic}
                    </span>
                  ))}
                </div>
              )}
              {result.id && (
                <div className="analysis-rating-row">
                  <span className="meta-label">Rate analysis</span>
                  <div className="analysis-rating-buttons">
                    {[0, 1, 2, 3, 4, 5].map((value) => (
                      <button
                        key={value}
                        type="button"
                        className={`analysis-rating-btn ${result.userRating === value ? 'active' : ''}`}
                        onClick={() => {
                          void rateAnalysis(result.id, value)
                        }}
                      >
                        {value}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </article>
            <div className="analysis-grid">
              <article className="panel">
                <h2>{result.companyName}</h2>
                <h3>Current State</h3>
                <ul>
                  {result.currentState.slice(0, visibleStateCount).map((item, index) => (
                    <li key={`${item}-${index}`}>
                      <AnalysisItem text={item} />
                    </li>
                  ))}
                </ul>
              </article>
              <article className="panel">
                <h3>Future Advice (TODO Plan)</h3>
                {result.todoPlan.length === 0 ? (
                  <p className="status-text">
                    This company is treated as a mature benchmark. No catch-up TODO plan is
                    generated.
                  </p>
                ) : (
                  <ol>
                    {result.todoPlan.slice(0, visibleTodoCount).map((item, index) => (
                      <li key={`${item}-${index}`}>
                        <AnalysisItem text={item} />
                      </li>
                    ))}
                  </ol>
                )}
              </article>
            </div>
            {!!result.revenueSeries?.length && (
              <article className="panel">
                <h3>Revenue vs expected revenue</h3>
                <RevenueChart series={result.revenueSeries} />
              </article>
            )}
            {!!result.revenueSeries?.length && (
              <div className="analysis-grid">
                <article className="panel">
                  <h3>Revenue growth trend</h3>
                  <GrowthBars series={result.revenueSeries} />
                </article>
                <article className="panel">
                  <h3>Gap to expected trajectory</h3>
                  <RevenueGapChart series={result.revenueSeries} />
                </article>
              </div>
            )}
            <article className="panel topic-panel">
              <h3>Topic Coverage</h3>
              <p className="status-text">Quick visual map of focus areas in this analysis.</p>
              <div className="topic-bars">
                {topicStats.map((topic) => {
                  const percent = Math.round((topic.score / maxTopicScore) * 100)
                  return (
                    <div key={topic.label} className="topic-row">
                      <span>{topic.label}</span>
                      <div className="topic-bar-track">
                        <div
                          className="topic-bar-fill"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                      <strong>{topic.score}</strong>
                    </div>
                  )
                })}
              </div>
            </article>
          </div>
        )}
      </section>

      <section className="result-card">
        <h3>Saved Analyses</h3>
        {history.length === 0 ? (
          <p className="status-text">No saved analyses yet.</p>
        ) : (
          <div className="saved-analysis-list">
            {history.map((item) => (
              <div
                key={item.id ?? `${item.companyName}-${item.createdAt}`}
                className="saved-analysis-item-row"
              >
                <button
                  type="button"
                  className="saved-analysis-item"
                  onClick={() => {
                    setResult(item)
                    setStatusText('Loaded saved analysis.')
                  }}
                >
                  <strong>{item.companyName}</strong>
                  <span>{item.createdAt ?? ''}</span>
                </button>
                <button
                  type="button"
                  className="saved-analysis-delete"
                  onClick={() => {
                    void deleteAnalysis(item.id)
                  }}
                  aria-label={`Delete analysis ${item.companyName}`}
                  title="Delete analysis"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

function App() {
  const location = useLocation()
  const [auth, setAuth] = useState<AuthData | null>(() => getStoredAuth())
  const [chats, setChats] = useState<ChatSession[]>([])
  const [activeChatId, setActiveChatId] = useState<number | null>(null)
  const [hasPendingNewChat, setHasPendingNewChat] = useState(false)
  const isChatRoute = location.pathname === '/'

  useEffect(() => {
    if (auth) {
      storeAuth(auth)
    } else {
      clearAuth()
    }
  }, [auth])

  const loadChats = async (token: string) => {
    const response = await fetch(`${apiBase}/chats`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) return
    const data = (await response.json()) as ChatSession[]
    setChats(data)
    if (data.length > 0) {
      setActiveChatId((prev) => prev ?? data[0].id)
    } else {
      setActiveChatId(null)
    }
  }

  const ensureChat = async (): Promise<number | null> => {
    if (!auth) return null
    const response = await fetch(`${apiBase}/chats`, {
      method: 'POST',
      headers: buildAuthHeaders(auth.token),
      body: JSON.stringify({ title: 'New chat' }),
    })
    if (!response.ok) return null
    const chat = (await response.json()) as ChatSession
    setChats((prev) => [chat, ...prev])
    setActiveChatId(chat.id)
    setHasPendingNewChat(false)
    return chat.id
  }

  const startNewChat = () => {
    if (hasPendingNewChat && activeChatId === null) return
    setHasPendingNewChat(true)
    setActiveChatId(null)
  }

  const refreshChats = async () => {
    if (!auth?.token) return
    await loadChats(auth.token)
  }

  const deleteChat = async (chatId: number) => {
    if (!auth?.token) return
    const response = await fetch(`${apiBase}/chats/${chatId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (!response.ok) return

    const remaining = chats.filter((chat) => chat.id !== chatId)
    setChats(remaining)
    setActiveChatId((prev) => (prev === chatId ? (remaining[0]?.id ?? null) : prev))
    if (remaining.length === 0) setHasPendingNewChat(false)
  }

  useEffect(() => {
    if (!auth?.token) return
    const run = async () => {
      await loadChats(auth.token)
    }
    run()
  }, [auth?.token])

  const logout = async () => {
    if (auth?.token) {
      try {
        await fetch(`${apiBase}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${auth.token}` },
        })
      } catch {
        // Keep logout simple on frontend; local cleanup still happens.
      }
    }
    setChats([])
    setActiveChatId(null)
    setHasPendingNewChat(false)
    setAuth(null)
  }

  if (!auth) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={setAuth} />} />
        <Route path="/register" element={<RegisterPage onLogin={setAuth} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <p className="brand">ChatConsultBot</p>
        <p className="user-badge">Signed in as @{auth.username}</p>
        <nav>
          <NavLink to="/" end className="nav-link">
            Chats
          </NavLink>
          <NavLink to="/analysis" className="nav-link">
            Company Analysis
          </NavLink>
        </nav>
        <button className="logout-button" type="button" onClick={logout}>
          Logout
        </button>
        {isChatRoute && (
          <section className="sidebar-chat-section">
            <button
              className="new-chat-button"
              type="button"
              onClick={startNewChat}
              disabled={hasPendingNewChat && activeChatId === null}
            >
              New chat
            </button>
            <div className="chat-list">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  className={`chat-item ${chat.id === activeChatId ? 'active' : ''}`}
                >
                  <button
                    className="chat-item-title"
                    onClick={() => {
                      setHasPendingNewChat(false)
                      setActiveChatId(chat.id)
                    }}
                    type="button"
                  >
                    {chat.title || 'New chat'}
                  </button>
                  <button
                    className="chat-delete-button"
                    type="button"
                    onClick={() => {
                      void deleteChat(chat.id)
                    }}
                    aria-label={`Delete chat ${chat.title}`}
                    title="Delete chat"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}
      </aside>
      <div className="main-content">
        <Routes>
          <Route
            path="/"
            element={
              <ChatPage
                token={auth.token}
                activeChatId={activeChatId}
                onEnsureChat={ensureChat}
                onRefreshChats={refreshChats}
              />
            }
          />
          <Route path="/analysis" element={<AnalysisPage token={auth.token} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}

export default App
