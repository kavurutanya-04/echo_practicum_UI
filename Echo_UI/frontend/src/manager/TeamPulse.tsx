import clsx from 'clsx'
import { Info, Loader2, MessagesSquare, RefreshCw, Sparkles, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Pulse } from '../lib/api'

const SHARE_STYLE: Record<string, string> = {
  most: 'bg-indigo-600 text-white',
  many: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-500/20 dark:text-indigo-200',
  some: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  'a few': 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

const TONE_DOT = { positive: 'bg-emerald-500', concern: 'bg-rose-500', mixed: 'bg-amber-500' }

function moodLabel(positive: number, negative: number) {
  if (positive >= 75) return 'Mostly positive'
  if (positive >= 55) return 'Generally positive'
  if (negative >= 40) return 'Mostly negative'
  return 'Mixed'
}

/** Slide-over "What your team is saying": mood per survey topic plus AI theme bullets, never individual comments. */
export default function TeamPulse({ managerId, start, end, periodLabel, onClose }: { managerId: string; start: string; end: string; periodLabel: string; onClose: () => void }) {
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
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [managerId, start, end])

  const themesByTopic = new Map((pulse?.themes ?? []).map((t) => [t.topic, t]))

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-950/30 backdrop-blur-[1px]" onClick={onClose} />
      <aside className="slide-in absolute inset-y-0 right-0 flex w-full max-w-lg flex-col bg-slate-50 shadow-2xl dark:bg-slate-950">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-white px-5 py-4 dark:border-slate-800 dark:bg-slate-900">
          <div>
            <div className="flex items-center gap-2 text-base font-semibold">
              <MessagesSquare className="size-5 text-indigo-500" /> What your team is saying
            </div>
            <div className="mt-0.5 text-xs text-slate-500">Survey responses · {periodLabel}</div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close">
            <X className="size-5" />
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {loading && !pulse ? (
            <div className="flex items-center gap-2 p-4 text-sm text-slate-500">
              <Loader2 className="size-4 animate-spin" /> Loading survey results…
            </div>
          ) : !pulse?.mood.length ? (
            <p className="p-4 text-sm text-slate-500">Not enough survey responses in this period to summarize. Groups with fewer than 5 responses are not shown.</p>
          ) : (
            <>
              {generating && (
                <div className="flex items-center gap-2 rounded-xl bg-indigo-50 px-3 py-2 text-xs text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">
                  <Sparkles className="size-3.5 animate-pulse" /> Writing a summary of what people are saying…
                </div>
              )}
              {error && !generating && (
                <div className="flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
                  <Info className="mt-0.5 size-3.5 shrink-0" />
                  <span>
                    Theme summary unavailable: {error} The mood bars below still come straight from the survey scores.{' '}
                    <button className="font-medium underline" onClick={() => load(true)}>Try again</button>
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
                    <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" title={`${topic.positive}% positive, ${topic.neutral}% neutral, ${topic.negative}% negative`}>
                      <div className="bg-emerald-500" style={{ width: `${topic.positive}%` }} />
                      <div className="bg-slate-300 dark:bg-slate-600" style={{ width: `${topic.neutral}%` }} />
                      <div className="bg-rose-500" style={{ width: `${topic.negative}%` }} />
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
                                <span className={clsx('mr-1.5 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide', SHARE_STYLE[theme.share])}>{theme.share}</span>
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
        </div>

        <div className="border-t border-slate-200 bg-white px-5 py-3 text-[11px] leading-relaxed text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          Mood bars use each response's own 1–5 score. Theme bullets are AI-written summaries of anonymous responses: no quotes, no individual
          comments, and wording copied from a response is removed automatically.
          {pulse?.generated_at && (
            <span className="ml-1">
              Summary written {new Date(pulse.generated_at).toLocaleDateString()}.
              <button className="ml-1 inline-flex items-center gap-0.5 font-medium text-indigo-600 hover:underline dark:text-indigo-400" onClick={() => load(true)} disabled={generating}>
                <RefreshCw className="size-3" /> Refresh
              </button>
            </span>
          )}
        </div>
      </aside>
    </div>
  )
}
