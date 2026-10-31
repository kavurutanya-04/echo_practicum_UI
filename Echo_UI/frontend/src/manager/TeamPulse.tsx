import clsx from 'clsx'
import { ArrowDown, ArrowRight, ArrowUp, Check, ChevronRight, Info, Loader2, MessagesSquare, PenLine, RefreshCw, Sparkles, Target, TriangleAlert, Undo2, X } from 'lucide-react'
import { useEffect, useState, type CSSProperties } from 'react'
import { api, type GapItem, type Pulse, type TeamUpdate, type TeamUpdates } from '../lib/api'
import { DraftNoteDialog } from './Brief'
import type { Watched } from './store'

export type PanelTab = 'changed' | 'goals' | 'gaps' | 'pulse'

/* ---------------- Team pulse tab (what the survey says, never individual comments) ---------------- */

const SHARE_STYLE: Record<string, string> = {
  most: 'bg-indigo-500 text-white',
  many: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-500/20 dark:text-indigo-200',
  some: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  'a few': 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

const TONE_DOT = { positive: 'bg-indigo-400', concern: 'bg-rose-300', mixed: 'bg-amber-300' }

function moodLabel(positive: number, negative: number) {
  if (positive >= 75) return 'Mostly positive'
  if (positive >= 55) return 'Generally positive'
  if (negative >= 40) return 'Mostly negative'
  return 'Mixed'
}

function PulseTab({ managerId, start, end, periodLabel }: { managerId: string; start: string; end: string; periodLabel: string }) {
  const [pulse, setPulse] = useState<Pulse | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  async function load(generate: boolean) {
    generate ? setGenerating(true) : setLoading(true)
    setError('')
    try {
      const result = await api.pulse(managerId, start, end, generate)
      setPulse(result)
      if (result.error) setError(result.error)
      // Write the summary automatically the first time this team and period is opened.
      if (!generate && !result.themes) await load(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      generate ? setGenerating(false) : setLoading(false)
    }
  }

  useEffect(() => {
    load(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [managerId, start, end])

  const themesByTopic = new Map((pulse?.themes ?? []).map((t) => [t.topic, t]))

  return (
    <>
      <p className="px-1 text-xs text-slate-500">Survey responses · {periodLabel}</p>
      {loading && !pulse ? (
        <Loading text="Loading survey results…" />
      ) : !pulse?.mood.length ? (
        <p className="p-2 text-sm text-slate-500">Not enough survey responses in this period to summarize. Groups with fewer than 5 responses are not shown.</p>
      ) : (
        <>
          {generating && (
            <div className="flex items-center gap-2 rounded-xl bg-indigo-50 px-3 py-2 text-xs text-indigo-800 dark:bg-indigo-500/10 dark:text-indigo-200">
              <Sparkles className="size-3.5 animate-pulse" /> Writing a summary of what people are saying…
            </div>
          )}
          {error && !generating && (
            <div className="flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
              <Info className="mt-0.5 size-3.5 shrink-0" />
              <span>
                Theme summary unavailable: {error} The mood bars below still come straight from the survey scores.{' '}
                <button className="font-medium underline" onClick={() => load(true)}>
                  Try again
                </button>
              </span>
            </div>
          )}
          {pulse.mood.map((topic) => {
            const summary = themesByTopic.get(topic.topic)
            return (
              <section key={topic.topic} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
                <div className="flex items-baseline justify-between gap-2">
                  <h3 className="text-sm font-semibold">{topic.topic}</h3>
                  <span className="text-xs text-slate-500">
                    {moodLabel(topic.positive, topic.negative)} · {topic.responses} responses
                  </span>
                </div>
                <div className="mt-2 flex h-2 gap-0.5 overflow-hidden rounded-full" title={`${topic.positive}% positive, ${topic.neutral}% neutral, ${topic.negative}% negative`}>
                  <div className="bg-indigo-400" style={{ width: `${topic.positive}%` }} />
                  <div className="bg-slate-200 dark:bg-slate-700" style={{ width: `${topic.neutral}%` }} />
                  <div className="bg-rose-300/80" style={{ width: `${topic.negative}%` }} />
                </div>
                <div className="mt-1 flex gap-3 text-[11px] text-slate-500">
                  <span>{topic.positive}% positive</span>
                  <span>{topic.neutral}% neutral</span>
                  <span>{topic.negative}% negative</span>
                </div>
                {summary && (
                  <div className="mt-3 space-y-2">
                    {summary.headline && <p className="text-sm font-medium">{summary.headline}</p>}
                    <ul className="space-y-1.5">
                      {summary.themes.map((theme, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
                          <span className={clsx('mt-2 size-1.5 shrink-0 rounded-full', TONE_DOT[theme.tone])} />
                          <span>
                            <span className={clsx('mr-1.5 rounded px-1.5 py-0.5 text-[10px] font-semibold', SHARE_STYLE[theme.share])}>{theme.share}</span>
                            {theme.text}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
            )
          })}
        </>
      )}
      <p className="px-1 text-[11px] leading-relaxed text-slate-500">
        Mood bars use each response's own 1–5 score. Theme bullets are AI-written summaries of anonymous responses: no quotes, no individual comments, and wording
        copied from a response is removed automatically.
        {pulse?.generated_at && (
          <span className="ml-1">
            Summary written {new Date(pulse.generated_at).toLocaleDateString()}.
            <button className="ml-1 inline-flex items-center gap-0.5 font-medium text-indigo-700 hover:underline dark:text-indigo-300" onClick={() => load(true)} disabled={generating}>
              <RefreshCw className="size-3" /> Refresh
            </button>
          </span>
        )}
      </p>
    </>
  )
}

/* ---------------- What changed tab ---------------- */

const UPDATE_STYLE: Record<TeamUpdate['tone'], { icon: typeof ArrowUp; color: string }> = {
  up: { icon: ArrowUp, color: 'var(--color-lime)' },
  down: { icon: ArrowDown, color: 'var(--color-cherry)' },
  flat: { icon: ArrowRight, color: 'var(--color-original)' },
  warn: { icon: TriangleAlert, color: 'var(--color-vanilla)' },
  todo: { icon: PenLine, color: 'var(--color-zerosugar)' },
}

function ChangedTab({ updates, busy, onAsk, onTab }: { updates: TeamUpdates; busy: boolean; onAsk: (q: string) => void; onTab: (t: PanelTab) => void }) {
  if (!updates.updates.length) return <p className="p-2 text-sm text-slate-500">No survey quarter falls inside this period, so there is nothing to compare yet. Try "All data".</p>
  return (
    <>
      <p className="px-1 text-xs text-slate-500">
        {updates.quarter}
        {updates.previous_quarter ? ` compared with ${updates.previous_quarter}` : ', the latest quarter in this period'}
      </p>
      {updates.updates.map((u) => {
        const style = UPDATE_STYLE[u.tone]
        const clickable = u.action === 'gaps' || (!!u.question && !busy)
        return (
          <button
            key={u.id}
            disabled={!clickable}
            onClick={() => (u.action === 'gaps' ? onTab('gaps') : u.question && onAsk(u.question))}
            className="group flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3.5 text-left transition enabled:hover:border-indigo-300 disabled:cursor-default dark:border-slate-800 dark:bg-slate-900 dark:enabled:hover:border-indigo-500/60"
          >
            <span className="agent-tint grid size-9 shrink-0 place-items-center rounded-full" style={{ '--agent': style.color } as CSSProperties}>
              <style.icon className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">{u.title}</span>
              <span className="block text-xs text-slate-500">{u.detail}</span>
            </span>
            {clickable && <ChevronRight className="size-4 shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-indigo-500" />}
          </button>
        )
      })}
      <p className="px-1 text-[11px] leading-relaxed text-slate-500">
        {busy ? 'An investigation is running. Open an update when it finishes. ' : 'Open an update to run its investigation and read the brief on the page. '}
        Calculated from your team's records and survey scores, without AI.
      </p>
    </>
  )
}

/* ---------------- Goals tab ---------------- */

const number = (text?: string) => {
  const match = text?.match(/-?\d+(\.\d+)?/)
  return match ? Number(match[0]) : null
}

/** Compare where a saved goal started with the latest value, using the goal's own wording. */
function goalStatus(baseline: string, now: string | undefined, goal: string) {
  const start = number(baseline)
  const current = number(now)
  if (current === null || start === null) return null
  const target = /above|at least|over/i.test(goal) ? number(goal) : null
  if (target !== null)
    return {
      label: current > target ? 'Reached' : current > start ? 'Improving' : current < start ? 'Behind' : 'No change yet',
      good: current >= start || current > target,
      progress: Math.min(100, (100 * current) / target),
    }
  if (/fewer|less|lower|reduce/i.test(goal)) return { label: current < start ? 'Improving' : current > start ? 'Behind' : 'No change yet', good: current <= start, progress: null }
  if (/steady|hold|keep/i.test(goal)) return { label: Math.abs(current - start) <= 2 ? 'Holding steady' : current > start ? 'Improving' : 'Slipping', good: current >= start - 2, progress: null }
  return null
}

function GoalsTab({ watch, updates }: { watch: Watched[]; updates: TeamUpdates }) {
  if (!watch.length)
    return (
      <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
        <span className="agent-tint grid size-11 place-items-center rounded-full" style={{ '--agent': 'var(--color-lime)' } as CSSProperties}>
          <Target className="size-5" />
        </span>
        <p className="text-sm font-medium">No goals yet</p>
        <p className="text-sm text-slate-500">Open a brief and choose "Track next quarter". Its measures will show here with how they are moving.</p>
      </div>
    )
  return (
    <>
      <p className="px-1 text-xs text-slate-500">"Now" is the latest quarter in the selected period{updates.quarter ? ` (${updates.quarter})` : ''}.</p>
      {watch.map((w) => {
        const now = updates.measures[w.metric]
        const status = goalStatus(w.baseline, now, w.goal)
        return (
          <section key={w.question + w.metric} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-start gap-2">
              <h3 className="flex-1 text-sm font-semibold">{w.metric}</h3>
              {status && (
                <span
                  className={clsx(
                    'shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium',
                    status.good ? 'bg-indigo-50 text-indigo-800 dark:bg-indigo-500/15 dark:text-indigo-200' : 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300',
                  )}
                >
                  {status.label}
                </span>
              )}
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {[
                ['Started at', w.baseline, 'text-slate-900 dark:text-white'],
                ['Now', now ?? '—', status ? (status.good ? 'text-indigo-700 dark:text-indigo-300' : 'text-rose-600 dark:text-rose-300') : 'text-slate-900 dark:text-white'],
                ['Aim', w.goal, 'text-slate-500'],
              ].map(([label, value, tone]) => (
                <div key={label}>
                  <div className="text-[11px] text-slate-500">{label}</div>
                  <div className={clsx('font-semibold tabular-nums', value.length > 6 ? 'text-sm' : 'text-xl', tone)}>{value}</div>
                </div>
              ))}
            </div>
            {status?.progress != null && (
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <div className="h-full rounded-full bg-indigo-400 transition-all" style={{ width: `${status.progress}%` }} />
              </div>
            )}
            <p className="mt-2 text-[11px] text-slate-500">
              {now === undefined ? 'Echo has no current value for this measure. Ask the question again to update it. ' : ''}
              Saved {new Date(w.savedAt).toLocaleDateString()} from "{w.question}"
            </p>
          </section>
        )
      })}
    </>
  )
}

/* ---------------- Recognition gaps tab ---------------- */

const AVATAR_COLORS = ['var(--color-cherry)', 'var(--color-original)', 'var(--color-zerosugar)', 'var(--color-vanilla)', 'var(--color-lime)']

function GapsTab({ updates, thanked, onThank }: { updates: TeamUpdates; thanked: Record<string, string>; onThank: (id: string, done: boolean) => void }) {
  const [view, setView] = useState<'open' | 'thanked'>('open')
  const [draft, setDraft] = useState<GapItem | null>(null)
  const open = updates.gaps.filter((g) => !thanked[g.contribution_id])
  const done = updates.gaps.filter((g) => thanked[g.contribution_id])
  const shown = view === 'open' ? open : done
  const stillOpen = Math.max(0, updates.gaps_total - done.length)

  return (
    <>
      <div className="flex items-end gap-6 px-1">
        <div>
          <div className="text-3xl font-semibold tabular-nums text-rose-500 dark:text-rose-300">{stillOpen}</div>
          <div className="text-xs text-slate-500">still open</div>
        </div>
        <div>
          <div className="text-3xl font-semibold tabular-nums text-indigo-600 dark:text-indigo-300">{done.length}</div>
          <div className="text-xs text-slate-500">marked thanked</div>
        </div>
        <p className="flex-1 pb-1 text-right text-xs text-slate-500">{updates.quarter}</p>
      </div>
      <p className="px-1 text-xs text-slate-500">Cross-team work another team praised, with no recognition note from you on record. A starting point for a conversation, not a rating.</p>
      <div className="flex gap-1 px-1">
        {(['open', 'thanked'] as const).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={clsx(
              'rounded-full px-3 py-1 text-xs font-medium transition',
              view === v ? 'bg-slate-700 text-white dark:bg-slate-200 dark:text-slate-900' : 'text-slate-500 ring-1 ring-slate-200 hover:text-slate-800 dark:ring-slate-700 dark:hover:text-slate-200',
            )}
          >
            {v === 'open' ? `Open (${open.length})` : `Thanked (${done.length})`}
          </button>
        ))}
      </div>
      {shown.length === 0 && (
        <p className="p-2 text-sm text-slate-500">{view === 'open' ? 'Nothing waiting. Every praised contribution in this list has been thanked.' : 'Mark a contribution as thanked once you have recognized it.'}</p>
      )}
      {shown.map((g, i) => (
        <section key={g.contribution_id} className="rounded-2xl border border-slate-200 bg-white p-3.5 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-start gap-3">
            <span className="agent-tint grid size-9 shrink-0 place-items-center rounded-full text-xs font-semibold" style={{ '--agent': AVATAR_COLORS[i % AVATAR_COLORS.length] } as CSSProperties}>
              {g.name
                .split(' ')
                .map((n) => n[0])
                .join('')}
            </span>
            <div className="min-w-0 flex-1">
              <div className="text-sm">
                <span className="font-semibold">{g.name}</span> <span className="text-slate-500">helped {g.team_helped}</span>
              </div>
              <div className="mt-0.5 text-xs leading-relaxed text-slate-500">
                {g.outcome} · {g.date} · {g.praise_reached_you ? 'their praise was sent to you' : "their praise didn't reach you"}
              </div>
            </div>
            <span
              className={clsx(
                'shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium',
                g.age_days > 60
                  ? 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300'
                  : g.age_days > 30
                    ? 'bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300'
                    : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
              )}
              title={`Days between the contribution and ${updates.as_of}`}
            >
              {g.age_days} days
            </span>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button onClick={() => setDraft(g)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium hover:border-indigo-300 dark:border-slate-700 dark:bg-slate-900">
              <PenLine className="size-3.5" /> Draft note
            </button>
            {view === 'open' ? (
              <button onClick={() => onThank(g.contribution_id, true)} className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-700">
                <Check className="size-3.5" /> Mark as thanked
              </button>
            ) : (
              <button onClick={() => onThank(g.contribution_id, false)} className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                <Undo2 className="size-3.5" /> Move back to open
              </button>
            )}
          </div>
        </section>
      ))}
      {updates.gaps_total > updates.gaps.length && <p className="px-1 text-xs text-slate-500">Showing the {updates.gaps.length} oldest of {updates.gaps_total}.</p>}
      <p className="px-1 text-[11px] text-slate-500">Marking as thanked is only saved in this browser. Echo never sends messages for you.</p>
      {draft && <DraftNoteDialog example={draft} onClose={() => setDraft(null)} />}
    </>
  )
}

/* ---------------- the panel ---------------- */

function Loading({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 p-4 text-sm text-slate-500">
      <Loader2 className="size-4 animate-spin" /> {text}
    </div>
  )
}

/** Slide-over "Your team": what changed, goals, recognition gaps and team pulse, over the same page. */
export default function TeamPulse({
  managerId,
  teamName,
  start,
  end,
  periodLabel,
  tab,
  onTab,
  onClose,
  updates,
  updatesError,
  unseen,
  busy,
  onAsk,
  watch,
  thanked,
  onThank,
}: {
  managerId: string
  teamName: string
  start: string
  end: string
  periodLabel: string
  tab: PanelTab
  onTab: (tab: PanelTab) => void
  onClose: () => void
  updates: TeamUpdates | null
  updatesError: unknown
  unseen: number
  busy: boolean
  onAsk: (question: string) => void
  watch: Watched[]
  thanked: Record<string, string>
  onThank: (id: string, done: boolean) => void
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const openGaps = updates ? Math.max(0, updates.gaps_total - updates.gaps.filter((g) => thanked[g.contribution_id]).length) : 0
  const tabs: { id: PanelTab; label: string; badge?: number; tone?: string }[] = [
    { id: 'changed', label: 'What changed', badge: unseen, tone: 'bg-indigo-500' },
    { id: 'goals', label: 'Goals' },
    { id: 'gaps', label: 'Gaps', badge: openGaps, tone: 'bg-rose-400' },
    { id: 'pulse', label: 'Team pulse' },
  ]

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-950/25 backdrop-blur-[1px]" onClick={onClose} />
      <aside className="slide-in absolute inset-y-0 right-0 flex w-full max-w-lg flex-col bg-slate-50 shadow-2xl dark:bg-slate-950" aria-label="Your team">
        <div className="border-b border-slate-200 bg-white px-5 pb-3 pt-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-lg font-semibold tracking-tight">Your team</div>
              <div className="text-xs text-slate-500">
                {teamName} · {periodLabel}
              </div>
            </div>
            <button onClick={onClose} className="rounded-lg p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close">
              <X className="size-5" />
            </button>
          </div>
          <div className="mt-3 flex gap-0.5 overflow-x-auto rounded-xl bg-slate-100 p-1 dark:bg-slate-800/70" role="tablist">
            {tabs.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => onTab(t.id)}
                className={clsx(
                  'flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition sm:text-sm',
                  tab === t.id ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200',
                )}
              >
                {t.id === 'pulse' && <MessagesSquare className="size-3.5" />}
                {t.label}
                {!!t.badge && <span className={clsx('rounded-full px-1.5 text-[10px] font-semibold leading-4 text-white', t.tone)}>{t.badge}</span>}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {tab === 'pulse' ? (
            <PulseTab managerId={managerId} start={start} end={end} periodLabel={periodLabel} />
          ) : updatesError ? (
            <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
              Couldn't load your team's updates: {updatesError instanceof Error ? updatesError.message : String(updatesError)}
            </p>
          ) : !updates ? (
            <Loading text="Checking your team's records…" />
          ) : tab === 'changed' ? (
            <ChangedTab updates={updates} busy={busy} onAsk={onAsk} onTab={onTab} />
          ) : tab === 'goals' ? (
            <GoalsTab watch={watch} updates={updates} />
          ) : (
            <GapsTab updates={updates} thanked={thanked} onThank={onThank} />
          )}
        </div>
      </aside>
    </div>
  )
}
