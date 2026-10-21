import clsx from 'clsx'
import { ArrowRight, ArrowUp, LogOut, MessageSquarePlus, Moon, PanelLeft, ShieldAlert, Sparkles, Square, Sun, Wrench, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '../components/Layout'
import { api, type Manager, type Meta } from '../lib/api'
import { agentStates, useRunEvents } from '../lib/events'
import { useAsync } from '../lib/useAsync'
import AgentStrip, { agentActivity } from './AgentStrip'
import AnswerBubble, { PendingBubble } from './AnswerBubble'
import { loadConversations, loadManagerCode, saveConversations, saveManagerCode, type Conversation, type Message } from './store'

const SUGGESTED = [
  'How is recognition trending for my team?',
  "What do this quarter's recognition metrics suggest?",
  'Show Recognition over eight quarters.',
  'Which weeks exceed available project hours?',
  'How many cross-team contributions lack a recognition note?',
  'Which survey area changed most over the last year?',
]

const PERIODS = [
  { id: 'all', label: 'All data (Oct 2024 – Sep 2026)', start: '2024-10-01', end: '2026-09-30' },
  { id: 'year', label: 'Last 12 months', start: '2025-10-01', end: '2026-09-30' },
  { id: 'quarter', label: 'Last quarter (Jul – Sep 2026)', start: '2026-07-01', end: '2026-09-30' },
]

function ThemeButton() {
  const [dark, setDark] = useTheme()
  return (
    <button onClick={() => setDark(!dark)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Toggle light or dark mode">
      {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  )
}

/* ---------------- entry ---------------- */

function Entry({ onEnter }: { onEnter: (manager: Manager) => void }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!code.trim()) return
    setChecking(true)
    setError('')
    try {
      onEnter(await api.lookupManager(code))
    } catch {
      setError("We couldn't find that manager code. Codes look like M14.")
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="relative grid min-h-full place-items-center overflow-hidden px-4 py-12">
      <div className="pointer-events-none absolute -top-40 left-1/2 size-[640px] -translate-x-1/2 rounded-full bg-indigo-500/15 blur-3xl" />
      <div className="absolute right-4 top-4"><ThemeButton /></div>
      <div className="relative w-full max-w-md">
        <div className="mb-8 text-center">
          <img src="/favicon.svg" alt="" className="mx-auto size-14" />
          <h1 className="mt-4 text-3xl font-semibold tracking-tight">Echo</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Ask questions about your team's recognition, workload and survey results — answered by five cooperating agents and checked before you see them.</p>
        </div>
        <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/5 dark:border-slate-800 dark:bg-slate-900">
          <label htmlFor="code" className="text-sm font-medium">Manager code</label>
          <div className="mt-2 flex gap-2">
            <input
              id="code"
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="e.g. M14"
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 font-mono text-lg tracking-wider outline-none transition focus:border-indigo-400 focus:ring-4 focus:ring-indigo-500/10 dark:border-slate-700 dark:bg-slate-950"
            />
            <button disabled={checking || !code.trim()} className="inline-flex items-center gap-1 rounded-xl bg-indigo-600 px-4 font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50">
              <ArrowRight className="size-5" />
            </button>
          </div>
          {error && <p className="mt-2 text-sm text-rose-600 dark:text-rose-400">{error}</p>}
          <p className="mt-4 text-xs text-slate-500">Prototype access: the code selects which team's synthetic data Echo may use. It is not a secure login.</p>
        </form>
        <p className="mt-6 text-center text-xs text-slate-400">
          All employee data is synthetic · Echo supports human review and does not make personnel decisions
        </p>
      </div>
    </div>
  )
}

/* ---------------- chat ---------------- */

function MessageRow({ message, active, status, refreshKey }: { message: Message; active: boolean; status: string; refreshKey: number }) {
  const run = useAsync(() => api.managerRun(message.runId), [message.runId, active, refreshKey])
  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-2.5 text-[15px] text-white shadow-sm">{message.question}</div>
      </div>
      <div className="flex gap-3">
        <img src="/favicon.svg" alt="" className="mt-1 size-7 shrink-0" />
        <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          {active || run.data?.meta.state === 'running' ? (
            <PendingBubble status={status} />
          ) : run.data ? (
            <AnswerBubble meta={run.data.meta} artifact={run.data.artifact} />
          ) : run.error ? (
            <p className="text-sm text-slate-500">This answer is no longer available.</p>
          ) : (
            <PendingBubble status="Loading…" />
          )}
        </div>
      </div>
    </div>
  )
}

function liveConnection(meta: Meta | null) {
  if (meta?.local_split) return { use_local_split: true, profile: null }
  const profile = meta?.profiles.find((p) => p.key_configured)
  return profile ? { use_local_split: false, profile: profile.name } : null
}

function Workspace({ manager, onLeave }: { manager: Manager; onLeave: () => void }) {
  const meta = useAsync(api.meta)
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations(manager.Manager_ID))
  const [currentId, setCurrentId] = useState<string | null>(conversations[0]?.id ?? null)
  const [question, setQuestion] = useState('')
  const [period, setPeriod] = useState('all')
  const [mode, setMode] = useState<'demo' | 'live'>('demo')
  const [activeRun, setActiveRun] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [error, setError] = useState('')
  const [sidebar, setSidebar] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  const current = conversations.find((c) => c.id === currentId) ?? null
  const stream = useRunEvents(activeRun ?? undefined, mode === 'demo' ? 70 : 0, 0)
  const states = useMemo(() => agentStates(stream.events), [stream.events])
  const activity = useMemo(() => agentActivity(stream.events), [stream.events])
  const busy = activeRun !== null
  const connection = liveConnection(meta.data)

  // The chat bubble mirrors whichever agent logged the most recent step.
  const lastAgent = [...stream.events].reverse().find((e) => e.agent && e.agent !== 'original' || e.agent === 'Original')?.agent
  const named = (Object.keys(activity) as (keyof typeof activity)[]).find((a) => a.toLowerCase() === (lastAgent ?? '').toLowerCase())
  const status = named ? `${named}: ${activity[named] ?? 'working'}…` : 'Starting the agents…'

  useEffect(() => {
    saveConversations(manager.Manager_ID, conversations)
  }, [conversations, manager.Manager_ID])
  useEffect(() => {
    if (stream.done) {
      setActiveRun(null)
      setRefreshKey((k) => k + 1)
    }
  }, [stream.done])
  // Braces matter: newer browsers return a Promise from scrollIntoView, which React would treat as a cleanup.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [current?.messages.length, busy])

  async function ask(text: string) {
    const q = text.trim()
    if (!q || busy) return
    if (mode === 'live' && !connection) return setError('No live model is configured. Use demo mode, or add a key in the technical view.')
    setError('')
    const range = PERIODS.find((p) => p.id === period)!
    try {
      const run = await api.startRun({
        manager_id: manager.Manager_ID,
        start_date: range.start,
        end_date: range.end,
        question: q,
        mode,
        ...(mode === 'live' ? connection : {}),
      })
      const message: Message = { question: q, runId: run.id, mode, askedAt: new Date().toISOString() }
      if (current) {
        setConversations((all) => all.map((c) => (c.id === current.id ? { ...c, messages: [...c.messages, message] } : c)))
      } else {
        const conversation: Conversation = { id: run.id, title: q, createdAt: message.askedAt, messages: [message] }
        setConversations((all) => [conversation, ...all])
        setCurrentId(conversation.id)
      }
      setQuestion('')
      setActiveRun(run.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const sidebarContent = (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <img src="/favicon.svg" alt="" className="size-8" />
        <span className="text-base font-semibold tracking-tight">Echo</span>
        <button className="ml-auto rounded-lg p-1.5 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800" onClick={() => setSidebar(false)} aria-label="Close menu">
          <X className="size-4" />
        </button>
      </div>
      <div className="px-3">
        <button
          onClick={() => {
            setCurrentId(null)
            setSidebar(false)
          }}
          className="flex w-full items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium transition hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          <MessageSquarePlus className="size-4" /> New chat
        </button>
      </div>
      <div className="mt-4 flex-1 overflow-y-auto px-3">
        <div className="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Recent chats</div>
        {conversations.length === 0 && <p className="px-2 text-xs text-slate-500">Your chats will appear here.</p>}
        {conversations.map((c) => (
          <button
            key={c.id}
            onClick={() => {
              setCurrentId(c.id)
              setSidebar(false)
            }}
            className={clsx(
              'block w-full truncate rounded-lg px-2 py-1.5 text-left text-sm transition',
              c.id === currentId ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
            )}
          >
            {c.title}
          </button>
        ))}
      </div>
      <div className="border-t border-slate-200 p-3 dark:border-slate-800">
        <div className="mb-2 flex items-center gap-2.5 px-1">
          <span className="grid size-8 place-items-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">
            {manager.Manager_Name.split(' ').map((n) => n[0]).join('')}
          </span>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium">{manager.Manager_Name}</div>
            <div className="truncate text-xs text-slate-500">{manager.Manager_ID} · {manager.Primary_Team}</div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={onLeave} className="flex flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
            <LogOut className="size-3.5" /> Switch manager
          </button>
          <Link to="/console" className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" title="Runs, evidence, connections">
            <Wrench className="size-3.5" /> Technical
          </Link>
        </div>
      </div>
    </div>
  )

  return (
    <div className="chat-shell flex h-full">
      <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:block dark:border-slate-800 dark:bg-slate-900/60">{sidebarContent}</aside>
      {sidebar && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-950/40" onClick={() => setSidebar(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-white dark:bg-slate-900">{sidebarContent}</aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
          <div className="mx-auto flex max-w-4xl items-center gap-3">
            <button className="rounded-lg p-1.5 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800" onClick={() => setSidebar(true)} aria-label="Open menu">
              <PanelLeft className="size-5" />
            </button>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">{manager.Primary_Team}</div>
              <div className="short-hide truncate text-xs text-slate-500">{manager.Primary_Department} · {manager.Pilot_Assigned_Employees} people</div>
            </div>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              disabled={busy}
              className="ml-auto max-w-[45%] rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-900"
              aria-label="Time period"
            >
              {PERIODS.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
            <ThemeButton />
          </div>
          <div className="mx-auto mt-3 max-w-4xl">
            <AgentStrip states={states} activity={activity} busy={busy} />
          </div>
        </header>

        <main className="min-h-48 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl space-y-8 px-4 py-6">
            {!current || current.messages.length === 0 ? (
              <div className="py-8 text-center">
                <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
                  <Sparkles className="size-6" />
                </span>
                <h2 className="mt-4 text-xl font-semibold tracking-tight">Hi {manager.Manager_Name.split(' ')[0]}, what would you like to know?</h2>
                <p className="mx-auto mt-2 max-w-lg text-sm text-slate-500 dark:text-slate-400">
                  Echo looks only at your team's data for the period you choose. Watch the agents above light up as they plan, query, chart and check your answer.
                </p>
                <div className="mx-auto mt-6 grid max-w-2xl gap-2 sm:grid-cols-2">
                  {SUGGESTED.map((q) => (
                    <button
                      key={q}
                      onClick={() => ask(q)}
                      disabled={busy}
                      className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm transition hover:border-indigo-300 hover:shadow-sm disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-indigo-500"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              current.messages.map((message) => (
                <MessageRow key={message.runId} message={message} active={message.runId === activeRun} status={status} refreshKey={refreshKey} />
              ))
            )}
            <div ref={bottom} />
          </div>
        </main>

        <footer className="border-t border-slate-200 bg-white/80 px-4 pb-4 pt-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
          <div className="mx-auto max-w-4xl">
            {current && current.messages.length > 0 && !busy && (
              <div className="short-hide mb-2 flex gap-2 overflow-x-auto pb-1">
                {SUGGESTED.map((q) => (
                  <button key={q} onClick={() => ask(q)} className="shrink-0 rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-indigo-500">
                    {q}
                  </button>
                ))}
              </div>
            )}
            {error && <p className="mb-2 text-sm text-rose-600 dark:text-rose-400">{error}</p>}
            <form
              onSubmit={(e) => {
                e.preventDefault()
                ask(question)
              }}
              className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm transition focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-500/10 dark:border-slate-700 dark:bg-slate-900"
            >
              <textarea
                rows={1}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    ask(question)
                  }
                }}
                placeholder={busy ? 'Echo is working on your question…' : 'Ask about your team…'}
                disabled={busy}
                className="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-[15px] outline-none placeholder:text-slate-400"
              />
              {busy ? (
                <button type="button" onClick={() => api.cancelRun(activeRun!).catch(() => undefined)} className="grid size-10 place-items-center rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900" aria-label="Stop">
                  <Square className="size-4" fill="currentColor" />
                </button>
              ) : (
                <button disabled={!question.trim()} className="grid size-10 place-items-center rounded-xl bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:opacity-40" aria-label="Send">
                  <ArrowUp className="size-5" />
                </button>
              )}
            </form>
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
              <div className="flex rounded-lg bg-slate-100 p-0.5 dark:bg-slate-800">
                {(['demo', 'live'] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    disabled={busy}
                    className={clsx('rounded-md px-2.5 py-0.5 font-medium capitalize', mode === m ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white' : '')}
                  >
                    {m === 'demo' ? 'Demo' : 'Live AI'}
                  </button>
                ))}
              </div>
              <span className="short-hide flex items-center gap-1">
                <ShieldAlert className="size-3" /> Synthetic data · supports human review, never personnel decisions
              </span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default function ManagerApp() {
  const [manager, setManager] = useState<Manager | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const saved = loadManagerCode()
    if (!saved) return setChecking(false)
    api
      .lookupManager(saved)
      .then(setManager)
      .catch(() => saveManagerCode(null))
      .finally(() => setChecking(false))
  }, [])

  if (checking) return null
  if (!manager)
    return (
      <Entry
        onEnter={(m) => {
          saveManagerCode(m.Manager_ID)
          setManager(m)
        }}
      />
    )
  return (
    <Workspace
      key={manager.Manager_ID}
      manager={manager}
      onLeave={() => {
        saveManagerCode(null)
        setManager(null)
      }}
    />
  )
}
