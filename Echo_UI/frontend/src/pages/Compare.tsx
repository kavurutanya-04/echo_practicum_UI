import { ArrowLeft, GitCompareArrows } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { CitedText } from '../components/run/Answer'
import { Badge, Card, CardHeader, Empty, ErrorNote, Spinner } from '../components/ui'
import { api, type RunDetail } from '../lib/api'
import { duration, STATE_TONE } from '../lib/format'
import { useAsync } from '../lib/useAsync'

function Column({ detail }: { detail: RunDetail }) {
  const { meta, artifact } = detail
  const review = artifact?.verification?.reviews?.at(-1)
  return (
    <Card>
      <CardHeader
        title={<Link to={`/console/runs/${meta.id}`} className="hover:text-indigo-600">{meta.question}</Link>}
        subtitle={`${meta.mode === 'demo' ? 'offline demo' : meta.profile} · ${meta.manager_id} · ${duration(meta.created_at, meta.finished_at)}`}
      />
      <div className="space-y-5 p-5 text-sm">
        <div className="flex flex-wrap gap-1.5">
          <Badge tone={STATE_TONE[meta.state] ?? 'slate'}>{meta.state}</Badge>
          {meta.verification && <Badge tone={STATE_TONE[meta.verification] ?? 'slate'}>review: {meta.verification}</Badge>}
          <Badge>{meta.api_calls ?? 0} API calls</Badge>
          <Badge>{artifact?.evidence?.length ?? 0} sources</Badge>
          <Badge>{artifact?.visualization?.charts?.length ?? 0} charts</Badge>
        </div>
        {artifact && (
          <p className="leading-relaxed">
            <CitedText text={artifact.answer} onCite={() => undefined} known={new Set()} />
          </p>
        )}
        {review && (
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">ZeroSugar ratings</h4>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
              {Object.entries(review.ratings ?? {}).map(([name, rating]) => (
                <div key={name} className="flex justify-between border-b border-dashed border-slate-200 py-1 dark:border-slate-800">
                  <dt className="text-slate-500">{name}</dt>
                  <dd className="tabular-nums">{rating.score}/3</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
        {artifact?.execution?.profiles_used && (
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Models used</h4>
            <ul className="space-y-1 font-mono text-xs">
              {Object.entries(artifact.execution.profiles_used).map(([profile, use]) => (
                <li key={profile}>
                  {use.model} — {use.api_calls} calls
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  )
}

export default function Compare() {
  const [params] = useSearchParams()
  const a = params.get('a')
  const b = params.get('b')
  const runs = useAsync(() => (a && b ? Promise.all([api.run(a), api.run(b)]) : Promise.resolve(null)), [a, b])

  return (
    <div className="space-y-6">
      <div>
        <Link to="/console/runs" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
          <ArrowLeft className="size-4" /> All runs
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">Compare runs</h1>
        <p className="mt-1 text-sm text-slate-500">Use identical questions and scopes when comparing models, so differences reflect the model.</p>
      </div>
      {runs.loading ? (
        <Spinner />
      ) : runs.error ? (
        <ErrorNote error={runs.error} />
      ) : !runs.data ? (
        <Empty icon={GitCompareArrows} title="Pick two runs">Select two runs on the Runs page, then choose Compare.</Empty>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {runs.data.map((detail) => (
            <Column key={detail.meta.id} detail={detail} />
          ))}
        </div>
      )}
    </div>
  )
}
