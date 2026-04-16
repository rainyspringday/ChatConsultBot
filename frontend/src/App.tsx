import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import './App.css'

type ChatSession = { id: number; title: string; createdAt: string }
type ChatMessage = { id: number; role: 'user' | 'assistant'; content: string; createdAt: string }
type AnalysisResult = { id?: number; companyName: string; currentState: string[]; todoPlan: string[]; createdAt?: string }

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
  chats,
  activeChatId,
  onSelectChat,
  onCreateChat,
  onRefreshChats,
  onDeleteChat,
}: {
  token: string
  chats: ChatSession[]
  activeChatId: number | null
  onSelectChat: (id: number) => void
  onCreateChat: () => Promise<void>
  onRefreshChats: () => Promise<void>
  onDeleteChat: (id: number) => Promise<void>
}) {
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])

  const canSubmit = useMemo(
    () => question.trim().length > 0 && !isLoading && activeChatId !== null,
    [question, isLoading, activeChatId],
  )

  useEffect(() => {
    const loadMessages = async () => {
      if (!activeChatId) {
        setMessages([])
        return
      }
      const response = await fetch(`${apiBase}/chats/${activeChatId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) {
        setMessages([])
        return
      }
      const data = (await response.json()) as ChatMessage[]
      setMessages(data)
    }
    loadMessages()
  }, [activeChatId, token])

  const submitQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const content = question.trim()
    if (!content || isLoading || !activeChatId) return

    const optimisticUserMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, optimisticUserMessage])
    setQuestion('')
    setIsLoading(true)

    try {
      const response = await fetch(`${apiBase}/chats/${activeChatId}/messages`, {
        method: 'POST',
        headers: buildAuthHeaders(token),
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

      const data = (await response.json()) as { answer?: string; chatTitle?: string }
      const answer = data.answer?.trim() || 'No answer returned.'

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: answer,
          createdAt: new Date().toISOString(),
        },
      ])
      await onRefreshChats()
    } catch (error) {
      const message =
        error instanceof Error
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
      setIsLoading(false)
    }
  }

  return (
    <section className="chat-layout">
      <aside className="chat-list-panel">
        <button className="new-chat-button" type="button" onClick={onCreateChat}>
          + New chat
        </button>
        <div className="chat-list">
          {chats.map((chat) => (
            <div
              key={chat.id}
              className={`chat-item ${chat.id === activeChatId ? 'active' : ''}`}
            >
              <button
                className="chat-item-title"
                onClick={() => onSelectChat(chat.id)}
                type="button"
              >
                {chat.title || 'New chat'}
              </button>
              <button
                className="chat-delete-button"
                type="button"
                onClick={() => onDeleteChat(chat.id)}
                aria-label={`Delete chat ${chat.title}`}
                title="Delete chat"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>
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
          placeholder="Write your text here..."
          rows={6}
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
  const [statusText, setStatusText] = useState(
    'Enter a company name to run a process analysis.',
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

  const runAnalysis = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const name = companyName.trim()
    if (!name || isLoading) return
    setIsLoading(true)
    setStatusText('Requesting analysis from future API endpoint...')

    try {
      const response = await fetch(`${apiBase}/analyze-company`, {
        method: 'POST',
        headers: buildAuthHeaders(token),
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
        id?: number
        companyName?: string
        currentState?: string[]
        todoPlan?: string[]
        createdAt?: string
      }

      setResult({
        id: data.id,
        companyName: data.companyName ?? name,
        currentState: data.currentState ?? [],
        todoPlan: data.todoPlan ?? [],
        createdAt: data.createdAt,
      })
      setStatusText('Analysis loaded from API.')
      loadHistory()
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

      <section className="result-card">
        <h3>Saved Analyses</h3>
        {history.length === 0 ? (
          <p className="status-text">No saved analyses yet.</p>
        ) : (
          <div className="saved-analysis-list">
            {history.map((item) => (
              <button
                type="button"
                key={item.id ?? `${item.companyName}-${item.createdAt}`}
                className="saved-analysis-item"
                onClick={() => {
                  setResult(item)
                  setStatusText('Loaded saved analysis.')
                }}
              >
                <strong>{item.companyName}</strong>
                <span>{item.createdAt ?? ''}</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

function App() {
  const [auth, setAuth] = useState<AuthData | null>(() => getStoredAuth())
  const [chats, setChats] = useState<ChatSession[]>([])
  const [activeChatId, setActiveChatId] = useState<number | null>(null)

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

  const createChat = async () => {
    if (!auth) return
    const response = await fetch(`${apiBase}/chats`, {
      method: 'POST',
      headers: buildAuthHeaders(auth.token),
      body: JSON.stringify({ title: 'New chat' }),
    })
    if (!response.ok) return
    const chat = (await response.json()) as ChatSession
    setChats((prev) => [chat, ...prev])
    setActiveChatId(chat.id)
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
      </aside>
      <div className="main-content">
        <Routes>
          <Route
            path="/"
            element={
              <ChatPage
                token={auth.token}
                chats={chats}
                activeChatId={activeChatId}
                onSelectChat={setActiveChatId}
                onCreateChat={createChat}
                onRefreshChats={refreshChats}
                onDeleteChat={deleteChat}
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
