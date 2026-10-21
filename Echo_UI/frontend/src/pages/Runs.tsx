import clsx from 'clsx'
import { GitCompareArrows, History, Plus, Search, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PageTitle } from '../components/Layout'
import { Badge, Button, Card, Empty, ErrorNote, inputClass, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { duration, fmtDate, STATE_TONE } from '../lib/format'
import { useAsync } from '../lib/useAsync'

export default function Runs() {
  const navigate = useNavigate()
  const runs = useAsync(api.runs)
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<'all' | 'demo' | 'live'>('all')
  const [selected, setSelected] = useState<string[]>([])

  const shown = (runs.data ?? []).filter(
    (run) =>
      (mode === 'all' || run.mode === mode) &&
      `${run.question} ${run.manager_id} ${run.profile} ${run.state}`.toLowerCase().includes(query.toLowerCase()),
  )

  const toggle = (id: string) =>
    setSelected((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current.slice(-1), id]))

  return (
    <>
      <PageTitle
        title="Runs"
        subtitle="Every question asked through the console, with its evidence, review and charts."
        action={
          <div className="flex gap-2">
            <Button icon={GitCompareArrows} disabled={selected.length !== 2} onClick={() => navigate(`/console/compare?a=${selected[0]}&b=${selected[1]}`)}>
              Compare {selected.length ? `(${selected.length}/2)` : ''}
            </Button>
            <Link to="/console">
              <Button variant="primary" icon={Plus}>New question</Button>
            </Link>
          </div>
        }
      />
      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 p-4 dark:border-slate-800">
          <div className="relative min-w-60 flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-400" />
            <input className={clsx(inputClass, 'pl-9')} placeholder="Search questions, managers, models…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <div className="flex rounded-xl bg-slate-100 p-1 text-sm dark:bg-slate-800/60">
            {(['all', 'live', 'demo'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={clsx('rounded-lg px-3 py-1 capitalize', mode === m ? 'bg-white shadow-sm dark:bg-slate-900' : 'text-slate-500')}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
        {runs.loading && !runs.data ? (
          <Spinner />
        ) : runs.error ? (
          <div className="p-4"><ErrorNote error={runs.error} /></div>
        ) : shown.length === 0 ? (
          <Empty icon={History} title="No runs match">Ask a question or run the offline demo to get started.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-slate-500">
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="w-10 px-4 py-3" />
                  <th className="px-2 py-3 font-medium">Question</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 font-medium">Connection</th>
                  <th className="px-3 py-3 text-right font-medium">Calls</th>
                  <th className="px-3 py-3 font-medium">When</th>
                  <th className="w-10 px-3 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {shown.map((run) => (
                  <tr key={run.id} className="group hover:bg-slate-50/70 dark:hover:bg-slate-800/30">
                    <td className="px-4 py-3">
                      <input type="checkbox" className="accent-indigo-600" checked={selected.includes(run.id)} onChange={() => toggle(run.id)} aria-label="Select for comparison" />
                    </td>
                    <td className="max-w-md px-2 py-3">
                      <Link to={`/console/runs/${run.id}`} className="block truncate font-medium hover:text-indigo-600 dark:hover:text-indigo-400">
                        {run.question}
                      </Link>
                      <div className="text-xs text-slate-500">
                        {run.manager_id} · {run.start_date} → {run.end_date}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1">
                        <Badge tone={STATE_TONE[run.state] ?? 'slate'}>{run.state}</Badge>
                        {run.verification && <Badge tone={STATE_TONE[run.verification] ?? 'slate'}>{run.verification}</Badge>}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-xs text-slate-500">{run.mode === 'demo' ? 'offline demo' : run.profile}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{run.api_calls ?? '—'}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-xs text-slate-500">
                      {fmtDate(run.created_at)}
                      <div>{duration(run.created_at, run.finished_at)}</div>
                    </td>
                    <td className="px-3 py-3">
                      {run.state !== 'running' && (
                        <button
                          className="rounded-lg p-1.5 text-slate-400 opacity-0 transition hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100 dark:hover:bg-rose-500/10"
                          aria-label="Delete run"
                          onClick={async () => {
                            if (!confirm('Delete this run and its files?')) return
                            await api.deleteRun(run.id)
                            runs.reload()
                          }}
                        >
                          <Trash2 className="size-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
