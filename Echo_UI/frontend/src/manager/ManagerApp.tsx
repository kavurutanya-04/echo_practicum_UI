import clsx from 'clsx'
import { ArrowRight, History, LogOut, MessagesSquare, Moon, Newspaper, PanelLeft, ShieldAlert, Sparkles, Square, Sun, Wrench, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '../components/Layout'
import { api, type Artifact, type Manager, type Meta } from '../lib/api'
import { agentStates, useRunEvents } from '../lib/events'
import { useAsync } from '../lib/useAsync'
import AgentStage from './AgentStage'
import { agentActivity } from './AgentStrip'
import Brief, { BriefPending } from './Brief'
import TeamPulse from './TeamPulse'
import { loadConversations, loadManagerCode, loadWatch, saveConversations, saveManagerCode, saveWatch, type Conversation, type Message, type Watched } from './store'

const SUGGESTED = [
  "Is my team's cross-team work being recognized?",
  'How is recognition trending for my team?',
  "What do this quarter's recognition metrics suggest?",
  'Show Recognition over eight quarters.',
  'Which weeks exceed available project hours?',
  'How many cross-team contributions lack a recognition note?',
  'Which survey area changed most over the last year?',
]

const GUARDRAIL_EXAMPLE = 'Who complained about recognition in the last survey?'

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

/* ---------------- newsroom ---------------- */

function liveConnection(meta: Meta | null) {
  if (meta?.local_split) return { use_local_split: true, profile: null }
  const profile = meta?.profiles.find((p) => p.key_configured)
  return profile ? { use_local_split: false, profile: profile.name } : null
}

const keyOf = (q: string) => q.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()

function Workspace({ manager, onLeave }: { manager: Manager; onLeave: () => void }) {
  const meta = useAsync(api.meta)
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations(manager.Manager_ID))
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [period, setPeriod] = useState('all')
  const [mode, setMode] = useState<'demo' | 'live'>('demo')
  const [activeRun, setActiveRun] = useState<string | null>(null)
  const [activePace, setActivePace] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const [error, setError] = useState('')
  const [sidebar, setSidebar] = useState(false)
  const [pulseOpen, setPulseOpen] = useState(false)
  const [watch, setWatch] = useState<Watched[]>(() => loadWatch(manager.Manager_ID))
  const range = PERIODS.find((p) => p.id === period)!
  const saved = useAsync(() => api.savedAnswers(manager.Manager_ID, range.start, range.end), [period, refreshKey])
  const savedSet = new Set((saved.data ?? []).map((s) => keyOf(s.question)))

  const current = conversations.find((c) => c.id === currentId) ?? null
  const message = current?.messages.at(-1) ?? null
  const viewRunId = message?.runId
  // The stage replays the active investigation step by step, or shows the finished state of the one being read.
  const stream = useRunEvents(activeRun ?? viewRunId, activeRun ? activePace : 0, 0)
  const states = useMemo(() => agentStates(stream.events), [stream.events])
  const activity = useMemo(() => agentActivity(stream.events), [stream.events])
  const busy = activeRun !== null
  const run = useAsync(() => (viewRunId ? api.managerRun(viewRunId) : Promise.resolve(null)), [viewRunId, refreshKey])
  const connection = liveConnection(meta.data)
  const tracked = !!message && watch.some((w) => w.question === message.question)

  const lastAgent = [...stream.events].reverse().find((e) => e.agent && e.agent !== 'original')?.agent
  const named = (Object.keys(activity) as (keyof typeof activity)[]).find((a) => a.toLowerCase() === (lastAgent ?? '').toLowerCase())
  const status = named ? `${named}: ${activity[named] ?? 'working'}…` : 'The editor is planning the investigation…'

  useEffect(() => {
    saveConversations(manager.Manager_ID, conversations)
  }, [conversations, manager.Manager_ID])
  useEffect(() => {
    if (stream.done && activeRun) {
      setActiveRun(null)
      setRefreshKey((k) => k + 1)
    }
  }, [stream.done, activeRun])

  async function ask(text: string) {
    const q = text.trim()
    if (!q || busy) return
    if (mode === 'live' && !connection) return setError('No live model is configured. Use Demo mode, or add a key in the technical view.')
    setError('')
    try {
      const started = await api.startRun({
        manager_id: manager.Manager_ID,
        start_date: range.start,
        end_date: range.end,
        question: q,
        mode,
        ...(mode === 'live' ? connection : {}),
      })
      const entry: Message = { question: q, runId: started.id, mode, askedAt: new Date().toISOString() }
      // Every question opens its own investigation.
      setConversations((all) => [{ id: started.id, title: q, createdAt: entry.askedAt, messages: [entry] }, ...all])
      setCurrentId(started.id)
      setQuestion('')
      setActivePace(started.mode === 'offline' ? 280 : started.mode === 'replay' ? 80 : started.mode === 'demo' ? 70 : 0)
      setActiveRun(started.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  function track(items: NonNullable<Artifact['watch']>) {
    if (!message) return
    const next = [...watch.filter((w) => w.question !== message.question), ...items.map((i) => ({ ...i, savedAt: new Date().toISOString(), question: message.question }))]
    setWatch(next)
    saveWatch(manager.Manager_ID, next)
  }

  const sidebarContent = (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <img src="/favicon.svg" alt="" className="size-8" />
        <div>
          <div className="text-base font-semibold leading-tight tracking-tight">Echo</div>
          <div className="text-[11px] text-slate-500">Your team's newsroom</div>
        </div>
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
          <Newspaper className="size-4" /> New investigation
        </button>
      </div>
      <div className="mt-4 flex-1 overflow-y-auto px-3">
        <div className="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Investigations</div>
        {conversations.length === 0 && <p className="px-2 text-xs text-slate-500">Your investigations will appear here.</p>}
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
            {c.messages.at(-1)?.question ?? c.title}
          </button>
        ))}
        {watch.length > 0 && (
          <>
            <div className="mb-1.5 mt-5 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Tracking next quarter</div>
            <ul className="space-y-1.5 px-2">
              {watch.map((w) => (
                <li key={w.question + w.metric} className="text-xs">
                  <div className="text-slate-700 dark:text-slate-300">{w.metric}</div>
                  <div className="text-slate-500">
                    now {w.baseline} · aim {w.goal}
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
      <div className="border-t border-slate-200 p-3 dark:border-slate-800">
        <div className="mb-2 flex items-center gap-2.5 px-1">
          <span className="grid size-8 place-items-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">
            {manager.Manager_Name.split(' ').map((n) => n[0]).join('')}
          </span>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium">{manager.Manager_Name}</div>
            <div className="truncate text-xs text-slate-500">
              {manager.Manager_ID} · {manager.Primary_Team}
            </div>
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
          <div className="mx-auto flex max-w-5xl items-center gap-3">
            <button className="rounded-lg p-1.5 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800" onClick={() => setSidebar(true)} aria-label="Open menu">
              <PanelLeft className="size-5" />
            </button>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">{manager.Primary_Team}</div>
              <div className="short-hide truncate text-xs text-slate-500">
                {manager.Primary_Department} · {manager.Pilot_Assigned_Employees} people
              </div>
            </div>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              disabled={busy}
              className="ml-auto max-w-[45%] rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-900"
              aria-label="Time period"
            >
              {PERIODS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
            <button
              onClick={() => setPulseOpen(true)}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 transition hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:text-slate-200 dark:hover:border-indigo-500"
              title="What your team is saying in surveys"
            >
              <MessagesSquare className="size-3.5" /> <span className="hidden sm:inline">Team pulse</span>
            </button>
            <ThemeButton />
          </div>
        </header>

        <main className="min-h-48 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-5xl space-y-5 px-4 py-6">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                ask(question)
              }}
              className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-2 pl-4 shadow-sm transition focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-500/10 dark:border-slate-700 dark:bg-slate-900"
            >
              <Newspaper className="size-5 shrink-0 text-indigo-500" />
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={busy}
                placeholder={busy ? 'The newsroom is working…' : mode === 'demo' ? 'What should the newsroom investigate? (Demo: pick a suggestion)' : 'What should the newsroom investigate?'}
                className="min-w-0 flex-1 bg-transparent py-2 text-[15px] outline-none placeholder:text-slate-400"
              />
              <div className="hidden rounded-lg bg-slate-100 p-0.5 text-[11px] sm:flex dark:bg-slate-800">
                {(['demo', 'live'] as const).map((m) => (
                  <button
                    type="button"
                    key={m}
                    onClick={() => setMode(m)}
                    disabled={busy}
                    className={clsx('rounded-md px-2.5 py-1 font-medium', mode === m ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white' : 'text-slate-500')}
                  >
                    {m === 'demo' ? 'Demo' : 'Live AI'}
                  </button>
                ))}
              </div>
              {busy ? (
                <button type="button" onClick={() => api.cancelRun(activeRun!).catch(() => undefined)} className="grid size-10 place-items-center rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900" aria-label="Stop">
                  <Square className="size-4" fill="currentColor" />
                </button>
              ) : (
                <button disabled={!question.trim()} className="grid size-10 place-items-center rounded-xl bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:opacity-40" aria-label="Investigate">
                  <ArrowRight className="size-5" />
                </button>
              )}
            </form>
            {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}
            {!busy && (
              <div className="flex flex-wrap gap-2">
                {SUGGESTED.map((q, i) => (
                  <button
                    key={q}
                    onClick={() => ask(q)}
                    className={clsx(
                      'inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs transition',
                      i === 0
                        ? 'border-indigo-300 bg-indigo-50 font-medium text-indigo-700 hover:bg-indigo-100 dark:border-indigo-500/40 dark:bg-indigo-500/10 dark:text-indigo-300'
                        : 'border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-indigo-500',
                    )}
                  >
                    {mode === 'demo' && savedSet.has(keyOf(q)) && <History className="size-3 text-indigo-500" />}
                    {i === 0 && <Sparkles className="size-3" />}
                    {q}
                  </button>
                ))}
                <button
                  onClick={() => ask(GUARDRAIL_EXAMPLE)}
                  className="inline-flex items-center gap-1 rounded-full border border-dashed border-rose-300 px-3 py-1 text-xs text-rose-700 transition hover:bg-rose-50 dark:border-rose-500/40 dark:text-rose-300 dark:hover:bg-rose-500/10"
                  title="See how Echo protects anonymous responses"
                >
                  <ShieldAlert className="size-3" /> Try one Echo won't answer
                </button>
              </div>
            )}

            <AgentStage
              states={states}
              activity={activity}
              busy={busy}
              headline={busy ? status : current ? 'Investigation complete — read the brief below' : 'Ask a question and watch the newsroom work'}
            />

            {!current ? (
              <section className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 md:grid-cols-[1.2fr_1fr] dark:border-slate-800 dark:bg-slate-900">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight">See the work your team does that you don't always hear about.</h2>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                    Hi {manager.Manager_Name.split(' ')[0]}. Echo is a small newsroom for your team: five agents investigate your question using only your team's data, check
                    each other's work, and hand you a brief you can act on — without exposing anyone's survey answers.
                  </p>
                  <button onClick={() => ask(SUGGESTED[0])} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">
                    <Sparkles className="size-4" /> Start with: {SUGGESTED[0]}
                  </button>
                </div>
                <ul className="space-y-3 text-sm">
                  {[
                    ['The work', 'What your people did for other teams', 'var(--color-cherry)'],
                    ['The feedback', 'Praise and recognition on record', 'var(--color-cherry)'],
                    ['The voice', 'What the team says, as themes only', 'var(--color-vanilla)'],
                  ].map(([title, text, color]) => (
                    <li key={title} className="flex gap-3 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                      <span className="mt-1 size-2.5 shrink-0 rounded-full" style={{ background: color }} />
                      <span>
                        <span className="font-medium">{title}</span>
                        <span className="block text-xs text-slate-500">{text}</span>
                      </span>
                    </li>
                  ))}
                  <li className="text-xs text-slate-500">ZeroSugar checks whether all three agree — and tells you when they don't.</li>
                </ul>
              </section>
            ) : (
              <section className="space-y-4">
                <h2 className="text-xl font-semibold tracking-tight">{message?.question}</h2>
                {busy || run.loading || run.data?.meta.state === 'running' ? (
                  <BriefPending activity={activity} />
                ) : run.data ? (
                  <Brief meta={run.data.meta} artifact={run.data.artifact} managerId={manager.Manager_ID} onOpenPulse={() => setPulseOpen(true)} onTrack={track} tracked={tracked} />
                ) : (
                  <p className="text-sm text-slate-500">This investigation is no longer available.</p>
                )}
              </section>
            )}
            <p className="flex items-center justify-center gap-1 pb-2 text-center text-[11px] text-slate-500">
              <ShieldAlert className="size-3" /> Synthetic data · supports human review, never personnel decisions
            </p>
          </div>
        </main>
      </div>
      {pulseOpen && <TeamPulse managerId={manager.Manager_ID} start={range.start} end={range.end} periodLabel={range.label} onClose={() => setPulseOpen(false)} />}
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
