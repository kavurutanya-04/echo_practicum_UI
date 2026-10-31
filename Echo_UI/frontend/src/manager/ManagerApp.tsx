import clsx from 'clsx'
import { ArrowRight, ChevronDown, ChevronUp, History, Plus, Presentation, LogOut, Moon, Newspaper, PanelLeft, ShieldAlert, Sparkles, Square, Sun, Users, Wrench, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '../components/Layout'
import { api, type Artifact, type Manager, type Meta } from '../lib/api'
import { agentStates, useRunEvents } from '../lib/events'
import { SERIES_COLORS } from '../lib/agents'
import { useAsync } from '../lib/useAsync'
import AgentStage, { AgentStageMini } from './AgentStage'
import { agentActivity } from './AgentStrip'
import Brief, { BriefPending } from './Brief'
import TeamPulse, { type PanelTab } from './TeamPulse'
import { loadConversations, loadManagerCode, loadSeen, loadThanked, loadWatch, saveConversations, saveManagerCode, saveSeen, saveThanked, saveWatch, type Conversation, type Message, type Watched } from './store'

// How many suggestions stay visible when the rest are hidden.
const SUGGESTED_SHORT = 3

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

/** Concentric arcs spreading from a point: the "echo" motif on the sign-in panel. */
function Ripples({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 600 600" className={className} aria-hidden fill="none">
      {[60, 115, 175, 240, 310, 385].map((r, i) => (
        <circle key={r} cx="300" cy="300" r={r} stroke="currentColor" strokeWidth={i === 0 ? 1.6 : 1} strokeOpacity={0.55 - i * 0.075} className="echo-ripple" style={{ animationDelay: `${i * 140}ms` }} />
      ))}
    </svg>
  )
}

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
    <div className="grid min-h-full lg:grid-cols-[1.1fr_1fr]">
      {/* Brand panel: deep sage-to-ink, the same in light and dark mode */}
      <section className="echo-entry-panel relative overflow-hidden px-6 pb-10 pt-8 text-white sm:px-12 lg:px-16 lg:py-14">
        {/* ripples spread from the top-right corner, clear of the text */}
        <Ripples className="pointer-events-none absolute -right-[330px] -top-[330px] hidden size-[660px] text-[#c8d3a8] lg:block" />
        <Ripples className="pointer-events-none absolute -right-52 -top-52 size-[520px] text-[#b9c6d6] lg:hidden" />
        <div className="relative flex h-full flex-col">
          <div className="flex items-center gap-3">
            <img src="/favicon.svg" alt="" className="size-10 rounded-xl ring-1 ring-white/20" />
            <span className="text-sm font-medium tracking-wide text-white/80">Your team's newsroom</span>
          </div>

          <div className="mt-10 max-w-xl lg:my-auto">
            <h1 className="font-display text-6xl font-semibold leading-none tracking-tight sm:text-7xl lg:text-8xl">Echo</h1>
            <p className="mt-5 font-display text-2xl leading-snug text-white/90 sm:text-3xl">See the work your team does that you don't always hear about.</p>
            <p className="mt-4 max-w-md text-[15px] leading-relaxed text-white/70">
              Ask about recognition, workload and survey results. Five agents investigate using only your team's data, check each other's work, and hand you a
              brief you can act on.
            </p>
          </div>


          <p className="mt-12 hidden text-xs text-white/50 lg:block">Every claim is checked before you see it. No individual survey answer is ever shown.</p>
        </div>
      </section>

      {/* Sign-in */}
      <section className="relative flex items-center justify-center bg-slate-50 px-6 py-12 sm:px-12 dark:bg-slate-950">
        <div className="absolute right-4 top-4">
          <ThemeButton />
        </div>
        <div className="w-full max-w-sm">
          <h2 className="font-display text-4xl font-semibold tracking-tight text-slate-900 dark:text-white">Welcome back</h2>
          <p className="mt-2 text-[15px] text-slate-600 dark:text-slate-400">Enter your manager code to open your team's newsroom.</p>

          <form onSubmit={submit} className="mt-8">
            <label htmlFor="code" className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Manager code
            </label>
            <input
              id="code"
              autoFocus
              autoComplete="off"
              spellCheck={false}
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="M14"
              aria-invalid={!!error}
              aria-describedby={error ? 'code-error' : 'code-note'}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3.5 font-mono text-2xl tracking-[0.2em] text-slate-900 shadow-sm outline-none transition placeholder:text-slate-300 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-400/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:placeholder:text-slate-600"
            />
            {error && (
              <p id="code-error" className="mt-2 text-sm text-rose-600 dark:text-rose-400">
                {error}
              </p>
            )}
            <button
              disabled={checking || !code.trim()}
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3.5 text-[15px] font-semibold text-white shadow-[0_10px_24px_-12px_rgb(65_74_40/0.7)] transition hover:bg-indigo-700 disabled:bg-indigo-300/70 disabled:shadow-none dark:disabled:bg-indigo-900/50 dark:disabled:text-indigo-200/50"
            >
              {checking ? 'Opening…' : 'Open my newsroom'}
              {!checking && <ArrowRight className="size-4" />}
            </button>
          </form>

          <div id="code-note" className="mt-8 space-y-2 border-t border-slate-200 pt-6 text-xs leading-relaxed text-slate-500 dark:border-slate-800 dark:text-slate-400">
            <p>Prototype access: the code selects which team's data Echo may use. It is not a secure login.</p>
            <p>Echo supports human review and does not make personnel decisions.</p>
          </div>
        </div>
      </section>
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

/** A small on/off preference remembered in this browser (layout choices only). */
function usePref(key: string, initial: boolean) {
  const [value, setValue] = useState(() => {
    try {
      const saved = localStorage.getItem(key)
      return saved === null ? initial : saved === '1'
    } catch {
      return initial
    }
  })
  const update = (next: boolean) => {
    setValue(next)
    try {
      localStorage.setItem(key, next ? '1' : '0')
    } catch {
      /* storage unavailable */
    }
  }
  return [value, update] as const
}

function Workspace({ manager, onLeave }: { manager: Manager; onLeave: () => void }) {
  const [stageSmall, setStageSmall] = usePref('echo-stage-small', false)
  const [tipsHidden, setTipsHidden] = usePref('echo-tips-hidden', false)
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
  const [panel, setPanel] = useState<PanelTab | null>(null)
  const [thanked, setThanked] = useState<Record<string, string>>(() => loadThanked(manager.Manager_ID))
  const [seen, setSeen] = useState(() => loadSeen(manager.Manager_ID))
  const [watch, setWatch] = useState<Watched[]>(() => loadWatch(manager.Manager_ID))
  const range = PERIODS.find((p) => p.id === period)!
  const saved = useAsync(() => api.savedAnswers(manager.Manager_ID, range.start, range.end), [period, refreshKey])
  const savedSet = new Set((saved.data ?? []).map((s) => keyOf(s.question)))
  const updates = useAsync(() => api.teamUpdates(manager.Manager_ID, range.start, range.end), [period])
  const seenKey = updates.data ? `${period}|${updates.data.as_of}` : ''
  const unseen = updates.data && seen !== seenKey ? updates.data.updates.length : 0
  const openGaps = updates.data ? Math.max(0, updates.data.gaps_total - updates.data.gaps.filter((g) => thanked[g.contribution_id]).length) : 0

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
  // Opening "What changed" counts as having seen this quarter's updates.
  useEffect(() => {
    if (panel === 'changed' && seenKey && seen !== seenKey) {
      setSeen(seenKey)
      saveSeen(manager.Manager_ID, seenKey)
    }
  }, [panel, seenKey, seen, manager.Manager_ID])
  const closePanel = useCallback(() => setPanel(null), [])

  function thank(id: string, done: boolean) {
    const next = { ...thanked }
    if (done) next[id] = new Date().toISOString()
    else delete next[id]
    setThanked(next)
    saveThanked(manager.Manager_ID, next)
  }
  useEffect(() => {
    // Only a finish signal from the run in progress ends it; the previous brief's stream can still report "done"
    // for a moment after a new question starts, which would otherwise skip the new run's animation.
    if (stream.done && activeRun && stream.done.id === activeRun) {
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
      if (current) {
        // A question asked inside an open investigation is added to it, and the investigation moves to the top.
        const id = current.id
        setConversations((all) => {
          const found = all.find((c) => c.id === id)
          if (!found) return [{ id: started.id, title: q, createdAt: entry.askedAt, messages: [entry] }, ...all]
          return [{ ...found, messages: [...found.messages, entry] }, ...all.filter((c) => c.id !== id)]
        })
      } else {
        // "New investigation" (or the start page): this question opens a fresh one.
        setConversations((all) => [{ id: started.id, title: q, createdAt: entry.askedAt, messages: [entry] }, ...all])
        setCurrentId(started.id)
      }
      setQuestion('')
      setActivePace(started.mode === 'offline' ? 280 : started.mode === 'replay' ? 80 : started.mode === 'demo' ? 70 : 0)
      setActiveRun(started.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  function track(items: NonNullable<Artifact['watch']>, question = message?.question) {
    if (!question) return
    const next = [...watch.filter((w) => w.question !== question), ...items.map((i) => ({ ...i, savedAt: new Date().toISOString(), question }))]
    setWatch(next)
    saveWatch(manager.Manager_ID, next)
  }

  // A fresh investigation: back to the start page, with an empty question box and the page scrolled to the top.
  function startNew() {
    if (busy) return
    setCurrentId(null)
    setQuestion('')
    setError('')
    document.getElementById('echo-main')?.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function present() {
    if (current) window.open(`/present/${encodeURIComponent(current.id)}`, '_blank', 'noopener')
  }

  const sidebarContent = (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <img src="/favicon.svg" alt="" className="size-8" />
        <div>
          <div className="text-base font-semibold leading-tight tracking-tight">Echo</div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400">Your team's newsroom</div>
        </div>
        <button className="ml-auto rounded-lg p-1.5 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800" onClick={() => setSidebar(false)} aria-label="Close menu">
          <X className="size-4" />
        </button>
      </div>
      <div className="px-3">
        <button
          onClick={() => {
            startNew()
            setSidebar(false)
          }}
          disabled={busy}
          title={busy ? 'Wait for the newsroom to finish this question' : 'Start a fresh investigation'}
          className="flex w-full items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium transition hover:border-indigo-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-indigo-500/60"
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
              c.id === currentId ? 'bg-indigo-50 font-medium text-indigo-800 dark:bg-indigo-500/10 dark:text-indigo-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
            )}
          >
            <span className="block truncate">{c.messages[0]?.question ?? c.title}</span>
            {c.messages.length > 1 && <span className="block text-[11px] font-normal text-slate-400">{c.messages.length} results</span>}
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
    <div className="chat-shell echo-wash flex h-full">
      <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-indigo-50/50 lg:block dark:border-slate-800 dark:bg-slate-900/60">{sidebarContent}</aside>
      {sidebar && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-950/40" onClick={() => setSidebar(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-indigo-50 dark:bg-slate-900">{sidebarContent}</aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="relative border-b border-slate-200 bg-white/75 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
          <div className="echo-ribbon absolute inset-x-0 bottom-0 h-0.5 opacity-70" aria-hidden />
          <div className="mx-auto flex max-w-5xl items-center gap-3">
            <button className="rounded-lg p-1.5 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800" onClick={() => setSidebar(true)} aria-label="Open menu">
              <PanelLeft className="size-5" />
            </button>
            <div className="flex shrink-0 items-center gap-2 sm:min-w-0 sm:shrink" title={`${manager.Manager_Name}, manager code ${manager.Manager_ID}`}>
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-800 dark:bg-indigo-500/20 dark:text-indigo-200">
                {manager.Manager_Name.split(' ').map((n) => n[0]).join('')}
              </span>
              <div className="hidden min-w-0 sm:block">
                <div className="truncate text-sm font-semibold">{manager.Manager_Name}</div>
                <div className="short-hide truncate text-xs text-slate-500">{manager.Manager_ID}</div>
              </div>
            </div>
            <div className="hidden h-8 w-px bg-slate-200 sm:block dark:bg-slate-700" />
            <div className="min-w-0">
              <div className="truncate text-sm font-medium">{manager.Primary_Team}</div>
              <div className="short-hide truncate text-xs text-slate-500">
                {manager.Primary_Department} · {manager.Pilot_Assigned_Employees} people
              </div>
            </div>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              disabled={busy}
              className="ml-auto max-w-[30%] rounded-lg sm:max-w-[40%] border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              aria-label="Time period"
            >
              {PERIODS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
            <button
              onClick={() => setPanel(unseen ? 'changed' : openGaps ? 'gaps' : 'changed')}
              className="relative inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-indigo-700"
              title="What changed, goals, recognition gaps and team pulse"
              aria-label={unseen ? `Your team, ${unseen} updates` : 'Your team'}
            >
              <Users className="size-3.5" /> <span className="hidden sm:inline">Your team</span>
              {unseen > 0 && <span className="rounded-full bg-white px-1.5 text-[10px] font-semibold leading-4 text-indigo-800">{unseen}</span>}
            </button>
            <ThemeButton />
          </div>
        </header>

        <main id="echo-main" className="min-h-48 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-5xl space-y-5 px-4 py-6">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                ask(question)
              }}
              className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-2 pl-4 shadow-[0_6px_24px_-14px_rgb(63_76_93/0.35)] transition focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-400/15 dark:border-slate-700 dark:bg-slate-900"
            >
              <Newspaper className="size-5 shrink-0 text-indigo-400" />
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={busy}
                placeholder={
                  busy
                    ? 'The newsroom is working…'
                    : current
                      ? mode === 'demo' ? 'Ask a follow-up in this investigation (Demo: pick a suggestion)' : 'Ask a follow-up in this investigation'
                      : mode === 'demo' ? 'What should the newsroom investigate? (Demo: pick a suggestion)' : 'What should the newsroom investigate?'
                }
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
                <button disabled={!question.trim()} className="grid size-10 place-items-center rounded-xl bg-indigo-600 text-white transition hover:bg-indigo-700 disabled:bg-indigo-200 dark:disabled:bg-indigo-500/20" aria-label="Investigate">
                  <ArrowRight className="size-5" />
                </button>
              )}
            </form>
            {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}
            {!busy && (
              <div className="flex flex-wrap items-center gap-2">
                {(tipsHidden ? SUGGESTED.slice(0, SUGGESTED_SHORT) : SUGGESTED).map((q, i) => (
                  <button
                    key={q}
                    onClick={() => ask(q)}
                    className={clsx(
                      'inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs transition',
                      i === 0
                        ? 'border-indigo-200 bg-indigo-50 font-medium text-indigo-800 hover:bg-indigo-100 dark:border-indigo-500/40 dark:bg-indigo-500/10 dark:text-indigo-200'
                        : 'border-slate-200 bg-white/70 text-slate-600 hover:border-indigo-300 hover:text-indigo-800 dark:border-slate-700 dark:bg-transparent dark:text-slate-300 dark:hover:border-indigo-500',
                    )}
                  >
                    {mode === 'demo' && savedSet.has(keyOf(q)) && <History className="size-3 text-indigo-600" />}
                    {i === 0 ? <Sparkles className="size-3" /> : <span className="size-1.5 shrink-0 rounded-full" style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} />}
                    {q}
                  </button>
                ))}
                <button
                  onClick={() => ask(GUARDRAIL_EXAMPLE)}
                  className="inline-flex items-center gap-1 rounded-full border border-dashed border-rose-200 px-3 py-1 text-xs text-rose-600 transition hover:bg-rose-50 dark:border-rose-500/40 dark:text-rose-300 dark:hover:bg-rose-500/10"
                  title="See how Echo protects anonymous responses"
                >
                  <ShieldAlert className="size-3" /> Try one Echo won't answer
                </button>
                {/* Only offered when there are more suggestions than the short list shows. */}
                {SUGGESTED.length > SUGGESTED_SHORT && (
                  <button
                    onClick={() => setTipsHidden(!tipsHidden)}
                    aria-expanded={!tipsHidden}
                    className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium text-indigo-700 transition hover:bg-indigo-50 dark:text-indigo-300 dark:hover:bg-indigo-500/10"
                  >
                    {tipsHidden ? (
                      <>
                        Show {SUGGESTED.length - SUGGESTED_SHORT} more <ChevronDown className="size-3.5" />
                      </>
                    ) : (
                      <>
                        Hide <ChevronUp className="size-3.5" />
                      </>
                    )}
                  </button>
                )}
              </div>
            )}

            {stageSmall ? (
              <AgentStageMini
                states={states}
                activity={activity}
                busy={busy}
                headline={busy ? status : current ? 'Investigation complete — read the brief below' : 'Ask a question and watch the newsroom work'}
                onExpand={() => setStageSmall(false)}
              />
            ) : (
              <AgentStage
                states={states}
                activity={activity}
                busy={busy}
                headline={busy ? status : current ? 'Investigation complete — read the brief below' : 'Ask a question and watch the newsroom work'}
                onMinimize={() => setStageSmall(true)}
              />
            )}

            {!current ? (
              <section className="grid gap-6 rounded-2xl border border-slate-200 bg-white p-6 md:grid-cols-[1.2fr_1fr] dark:border-slate-800 dark:bg-slate-900">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight">See the work your team does that you don't always hear about.</h2>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                    Hi {manager.Manager_Name.split(' ')[0]}. Echo is a small newsroom for your team: five agents investigate your question using only your team's data, check
                    each other's work, and hand you a brief you can act on — without exposing anyone's survey answers.
                  </p>
                  <button onClick={() => ask(SUGGESTED[0])} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700">
                    <Sparkles className="size-4" /> Start with: {SUGGESTED[0]}
                  </button>
                </div>
                <ul className="space-y-3 text-sm">
                  {[
                    ['The work', 'What your people did for other teams', 'var(--color-cherry)'],
                    ['The feedback', 'Praise and recognition on record', 'var(--color-cherry)'],
                    ['The voice', 'What the team says, as themes only', 'var(--color-vanilla)'],
                  ].map(([title, text, color]) => (
                    <li key={title} className="agent-wash flex gap-3 rounded-xl p-3" style={{ '--agent': color } as React.CSSProperties}>
                      <span className="mt-1 size-2.5 shrink-0 rounded-full" style={{ background: color }} />
                      <span>
                        <span className="font-medium">{title}</span>
                        <span className="block text-xs text-slate-500 dark:text-slate-400">{text}</span>
                      </span>
                    </li>
                  ))}
                  <li className="flex items-center gap-1.5 text-xs text-slate-500"><span className="size-2 rounded-full" style={{ background: 'var(--color-zerosugar)' }} />ZeroSugar checks whether all three agree — and tells you when they don't.</li>
                </ul>
              </section>
            ) : (
              <>
                {/* The investigation's bar: how many results, a fresh start, and the presentation. */}
                <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 px-4 py-2.5 dark:border-slate-800 dark:bg-slate-900/80">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-semibold">{current.messages[0]?.question ?? current.title}</div>
                    <div className="text-xs text-slate-500">
                      Investigation · {current.messages.length} result{current.messages.length === 1 ? '' : 's'} · ask a follow-up above to add another
                    </div>
                  </div>
                  <button
                    onClick={startNew}
                    disabled={busy}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-indigo-300 hover:text-indigo-800 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                  >
                    <Plus className="size-3.5" /> New investigation
                  </button>
                  <button
                    onClick={present}
                    disabled={busy}
                    title="Open all results in this investigation as a presentation in a new tab"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Presentation className="size-3.5" /> Present
                  </button>
                </div>

                <section className="space-y-4">
                  {current.messages.length > 1 && (
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-indigo-700 dark:text-indigo-300">
                      Result {current.messages.length} of {current.messages.length} · latest
                    </div>
                  )}
                  <h2 className="text-xl font-semibold tracking-tight">{message?.question}</h2>
                  {busy || run.loading || run.data?.meta.state === 'running' ? (
                    <BriefPending activity={activity} />
                  ) : run.data ? (
                    <Brief meta={run.data.meta} artifact={run.data.artifact} managerId={manager.Manager_ID} onOpenPulse={() => setPanel('pulse')} onTrack={track} tracked={tracked} />
                  ) : (
                    <p className="text-sm text-slate-500">This investigation is no longer available.</p>
                  )}
                </section>

                {current.messages.length > 1 && (
                  <section className="space-y-2.5">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Earlier in this investigation</div>
                    {current.messages
                      .slice(0, -1)
                      .map((m, i) => ({ m, n: i + 1 }))
                      .reverse()
                      .map(({ m, n }) => (
                        <EarlierResult
                          key={m.runId}
                          message={m}
                          number={n}
                          total={current.messages.length}
                          managerId={manager.Manager_ID}
                          onOpenPulse={() => setPanel('pulse')}
                          onTrack={(items) => track(items, m.question)}
                          tracked={watch.some((w) => w.question === m.question)}
                        />
                      ))}
                  </section>
                )}
              </>
            )}
            <p className="flex items-center justify-center gap-1 pb-2 text-center text-[11px] text-slate-400">
              <ShieldAlert className="size-3" /> Synthetic data · supports human review, never personnel decisions
            </p>
          </div>
        </main>
      </div>
      {panel && (
        <TeamPulse
          managerId={manager.Manager_ID}
          teamName={manager.Primary_Team}
          start={range.start}
          end={range.end}
          periodLabel={range.label}
          tab={panel}
          onTab={setPanel}
          onClose={closePanel}
          updates={updates.data}
          updatesError={updates.error}
          unseen={unseen}
          busy={busy}
          onAsk={(q) => {
            setPanel(null)
            ask(q)
          }}
          watch={watch}
          thanked={thanked}
          onThank={thank}
        />
      )}
    </div>
  )
}

/** An earlier result in the investigation: folded to its question and first line, opens to the full brief. */
function EarlierResult({
  message,
  number,
  total,
  managerId,
  onOpenPulse,
  onTrack,
  tracked,
}: {
  message: Message
  number: number
  total: number
  managerId: string
  onOpenPulse: () => void
  onTrack: (items: NonNullable<Artifact['watch']>) => void
  tracked: boolean
}) {
  const [open, setOpen] = useState(false)
  const run = useAsync(() => api.managerRun(message.runId), [message.runId])
  const firstLine = (run.data?.artifact?.answer ?? '').replace(/\s*\[[A-Za-z]+\d*(?::[A-Za-z0-9_-]+)?\]/g, '').split(/(?<=\.)\s/)[0]
  return (
    <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-start gap-3 px-4 py-3 text-left">
        <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-indigo-50 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-200">{number}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold">{message.question}</span>
          <span className="block truncate text-xs text-slate-500">
            Result {number} of {total} · {new Date(message.askedAt).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
            {firstLine ? ` · ${firstLine}` : ''}
          </span>
        </span>
        <ChevronDown className={clsx('mt-1 size-4 shrink-0 text-slate-400 transition', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="border-t border-slate-100 p-4 dark:border-slate-800">
          {run.data ? (
            <Brief meta={run.data.meta} artifact={run.data.artifact} managerId={managerId} onOpenPulse={onOpenPulse} onTrack={onTrack} tracked={tracked} />
          ) : run.loading ? (
            <p className="text-sm text-slate-500">Loading…</p>
          ) : (
            <p className="text-sm text-slate-500">This result is no longer available.</p>
          )}
        </div>
      )}
    </div>
  )
}

/** A short welcome between sign-in and the newsroom; the workspace loads underneath. Click to skip. */
function Welcome({ manager, onDone }: { manager: Manager; onDone: () => void }) {
  const first = manager.Manager_Name.trim().split(/\s+/)[0] || manager.Manager_Name
  const [leaving, setLeaving] = useState(false)
  useEffect(() => {
    const out = window.setTimeout(() => setLeaving(true), 2200)
    const gone = window.setTimeout(onDone, 3400) // in case the fade-out event never fires
    return () => {
      window.clearTimeout(out)
      window.clearTimeout(gone)
    }
  }, [onDone])
  return (
    <div
      role="status"
      aria-live="polite"
      onClick={() => setLeaving(true)}
      onTransitionEnd={(event) => event.target === event.currentTarget && leaving && onDone()}
      className={clsx(
        'echo-entry-panel fixed inset-0 z-[100] grid cursor-pointer place-items-center overflow-hidden px-6 text-center text-white transition-all duration-700 ease-in-out',
        leaving ? 'pointer-events-none scale-[1.02] opacity-0' : 'opacity-100',
      )}
    >
      <Ripples className="pointer-events-none absolute left-1/2 top-1/2 size-[760px] -translate-x-1/2 -translate-y-1/2 overflow-visible text-[#c8d3a8]" />
      <div className="relative">
        <h1 className="echo-welcome-rise font-display text-5xl font-semibold tracking-tight sm:text-7xl">Hi {first},</h1>
        <p className="echo-welcome-rise mt-4 font-display text-2xl text-white/90 sm:text-3xl" style={{ animationDelay: '250ms' }}>
          Good to see you back!
        </p>
        <p className="echo-welcome-rise mt-8 text-sm tracking-wide text-[#c8d3a8]" style={{ animationDelay: '550ms' }}>
          Opening your newsroom · {manager.Primary_Team}
        </p>
      </div>
    </div>
  )
}

export default function ManagerApp() {
  const [manager, setManager] = useState<Manager | null>(null)
  const [checking, setChecking] = useState(true)
  const [welcome, setWelcome] = useState(false)
  const endWelcome = useCallback(() => setWelcome(false), [])

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
          setWelcome(true)
        }}
      />
    )
  return (
    <>
      <Workspace
        key={manager.Manager_ID}
        manager={manager}
        onLeave={() => {
          saveManagerCode(null)
          setManager(null)
        }}
      />
      {welcome && <Welcome manager={manager} onDone={endWelcome} />}
    </>
  )
}
