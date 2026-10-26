import clsx from 'clsx'
import { ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import type { Artifact } from '../../lib/api'
import { STATE_TONE } from '../../lib/format'
import { Badge, Empty } from '../ui'

const asText = (value: unknown) => (typeof value === 'string' ? value : JSON.stringify(value))

/** ZeroSugar's rubric ratings, issues and per-draft decisions. */
export default function Review({ artifact }: { artifact: Artifact }) {
  const reviews = artifact.verification?.reviews ?? []
  const [selected, setSelected] = useState(Math.max(0, reviews.length - 1))
  if (!reviews.length) return <Empty icon={ShieldCheck} title="No review recorded">The run ended before ZeroSugar reviewed a draft.</Empty>
  const review = reviews[selected]
  const ratings = Object.entries(review.ratings ?? {})
  const average = ratings.length ? ratings.reduce((sum, [, r]) => sum + r.score, 0) / ratings.length : 0

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Badge tone={STATE_TONE[artifact.verification.decision ?? ''] ?? 'slate'} className="!text-sm">
          Final decision: {artifact.verification.decision ?? '—'}
        </Badge>
        <span className="text-sm text-slate-500">
          {artifact.verification.completed_reviews ?? reviews.length} completed review{(artifact.verification.completed_reviews ?? reviews.length) === 1 ? '' : 's'}{artifact.verification.status === 'failed' ? ' · latest review unfinished' : ''} · average {average.toFixed(2)} / 3
        </span>
        {reviews.length > 1 && (
          <div className="ml-auto flex gap-1">
            {reviews.map((r, i) => (
              <button
                key={i}
                onClick={() => setSelected(i)}
                className={clsx('rounded-lg px-2.5 py-1 text-xs font-medium', i === selected ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300')}
              >
                Draft {i + 1} · {r.decision}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {ratings.map(([name, rating]) => (
          <div key={name} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
            <div className="flex items-center justify-between text-sm font-medium">
              {name}
              <span className="tabular-nums text-slate-500">{rating.score}/3</span>
            </div>
            <div className="mt-2 flex gap-1">
              {[1, 2, 3].map((step) => (
                <span
                  key={step}
                  className={clsx(
                    'h-1.5 flex-1 rounded-full',
                    step <= rating.score ? (rating.score === 3 ? 'bg-emerald-500' : rating.score === 2 ? 'bg-amber-500' : 'bg-rose-500') : 'bg-slate-200 dark:bg-slate-700',
                  )}
                />
              ))}
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">{rating.rationale}</p>
          </div>
        ))}
      </div>

      {review.uncertainty && (
        <div className="rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-800/50">
          <span className="font-medium">Reviewer uncertainty: </span>
          <span className="text-slate-600 dark:text-slate-300">{review.uncertainty}</span>
        </div>
      )}

      {[...(review.issues ?? []), ...(review.deterministic_issues ?? [])].length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold">Issues raised</h4>
          <ul className="space-y-2">
            {[...(review.issues ?? []), ...(review.deterministic_issues ?? [])].map((issue, i) => (
              <li key={i} className="rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-sm dark:border-amber-500/20 dark:bg-amber-500/5">
                {asText(issue)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
