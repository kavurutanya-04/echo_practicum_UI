import clsx from 'clsx'
import { Handshake, LayoutDashboard, MessageSquareText, Sparkles, TrendingDown, TrendingUp, Users } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { PageTitle } from '../components/Layout'
import { Card, CardHeader, Empty, ErrorNote, inputClass, Spinner, Stat } from '../components/ui'
import { SERIES_COLORS } from '../lib/agents'
import { api, type SurveyRow } from '../lib/api'
import { fmtQuarter } from '../lib/format'
import { useAsync } from '../lib/useAsync'

type Metric = 'Mean_Score' | 'Favorable_Percent'

function heatColor(value: number | null) {
  if (value === null) return 'transparent'
  // 40% → rose, 70% → amber, 90% → emerald
  const hue = Math.max(0, Math.min(140, ((value - 40) / 50) * 140))
  return `hsl(${hue} 70% 50% / 0.22)`
}

export default function Dashboard() {
  const managers = useAsync(api.managers)
  const [manager, setManager] = useState('M14')
  const [start, setStart] = useState('2024-10-01')
  const [end, setEnd] = useState('2026-09-30')
  const [metric, setMetric] = useState<Metric>('Mean_Score')
  const overview = useAsync(() => api.overview(manager, start, end), [manager, start, end])

  const { dates, dimensions, byKey } = useMemo(() => {
    const rows = (overview.data?.survey ?? []).filter((r) => r.Dimension !== 'eNPS')
    const dates = [...new Set(rows.map((r) => r.Survey_Date))].sort()
    const dimensions = [...new Set(rows.map((r) => r.Dimension))]
    const byKey = new Map<string, SurveyRow>()
    for (const row of rows) byKey.set(`${row.Dimension}|${row.Survey_Date}`, row)
    return { dates, dimensions, byKey }
  }, [overview.data])

  // Eight overlapping lines are hard to read, so start with four core dimensions visible.
  const [hidden, setHidden] = useState<string[]>(['Role clarity', 'Team climate', 'Development', 'Benefits'])
  const chartData = dates.map((d) => ({
    quarter: fmtQuarter(d),
    ...Object.fromEntries(dimensions.map((dim) => [dim, byKey.get(`${dim}|${d}`)?.[metric] ?? null])),
  }))

  const enps = (overview.data?.survey ?? []).filter((r) => r.Dimension === 'eNPS').sort((a, b) => a.Survey_Date.localeCompare(b.Survey_Date))
  const latest = dates.at(-1)
  const previous = dates.at(-2)
  const recognition = latest ? byKey.get(`Recognition|${latest}`) : undefined
  const recognitionPrev = previous ? byKey.get(`Recognition|${previous}`) : undefined
  const delta = recognition?.Mean_Score != null && recognitionPrev?.Mean_Score != null ? recognition.Mean_Score - recognitionPrev.Mean_Score : null

  return (
    <>
      <PageTitle title="Team dashboard" subtitle="Deterministic survey metrics from Echo's scoped data layer — no model calls, no quota." />
      <Card className="mb-6">
        <div className="grid gap-4 p-4 sm:grid-cols-3">
          <select className={inputClass} value={manager} onChange={(e) => setManager(e.target.value)} aria-label="Manager">
            {(managers.data ?? []).map((m) => (
              <option key={m.Manager_ID} value={m.Manager_ID}>
                {m.Manager_ID} · {m.Manager_Name} · {m.Primary_Team}
              </option>
            ))}
          </select>
          <input type="date" className={inputClass} value={start} min="2024-10-01" max={end} onChange={(e) => setStart(e.target.value)} aria-label="From" />
          <input type="date" className={inputClass} value={end} min={start} max="2026-09-30" onChange={(e) => setEnd(e.target.value)} aria-label="To" />
        </div>
      </Card>

      {overview.loading && !overview.data ? (
        <Spinner />
      ) : overview.error ? (
        <ErrorNote error={overview.error} />
      ) : !overview.data || !dates.length ? (
        <Empty icon={LayoutDashboard} title="No survey results in this scope">Groups with fewer than 5 responses are suppressed.</Empty>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Pilot employees in scope" value={overview.data.headcount} hint={overview.data.teams.join(', ')} icon={Users} />
            <Stat label="Cross-team contributions" value={overview.data.contributions.toLocaleString()} hint="Recorded in the window" icon={Handshake} />
            <Stat label="Survey comments" value={overview.data.comments.toLocaleString()} hint="Anonymous, eligible groups only" icon={MessageSquareText} />
            <Stat
              label={`Recognition · ${latest ? fmtQuarter(latest) : ''}`}
              value={recognition?.Mean_Score?.toFixed(2) ?? '—'}
              icon={delta !== null && delta < 0 ? TrendingDown : TrendingUp}
              hint={
                delta !== null ? (
                  <span className={delta >= 0 ? 'text-emerald-600' : 'text-rose-600'}>
                    {delta >= 0 ? '+' : ''}
                    {delta.toFixed(2)} vs previous quarter · {recognition?.Favorable_Percent}% favorable
                  </span>
                ) : undefined
              }
            />
          </div>

          <Card>
            <CardHeader
              title="Survey dimensions over time"
              subtitle="Click a legend item to hide it. Only groups with at least 5 responses are shown."
              icon={TrendingUp}
              action={
                <div className="flex rounded-xl bg-slate-100 p-1 text-xs dark:bg-slate-800/60">
                  {(
                    [
                      ['Mean_Score', 'Mean score (1–5)'],
                      ['Favorable_Percent', 'Favorable %'],
                    ] as const
                  ).map(([id, label]) => (
                    <button key={id} onClick={() => setMetric(id)} className={clsx('rounded-lg px-2.5 py-1', metric === id ? 'bg-white shadow-sm dark:bg-slate-900' : 'text-slate-500')}>
                      {label}
                    </button>
                  ))}
                </div>
              }
            />
            <div className="h-80 p-4 text-slate-400">
              <ResponsiveContainer>
                <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} stroke="currentColor" vertical={false} />
                  <XAxis dataKey="quarter" stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} width={40} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                  <Legend
                    wrapperStyle={{ fontSize: 12, cursor: 'pointer' }}
                    onClick={(item) => {
                      const key = String(item.dataKey)
                      setHidden((h) => (h.includes(key) ? h.filter((x) => x !== key) : [...h, key]))
                    }}
                  />
                  {dimensions.map((dim, i) => (
                    <Line key={dim} dataKey={dim} hide={hidden.includes(dim)} type="linear" stroke={SERIES_COLORS[i % SERIES_COLORS.length]} strokeWidth={2} dot={{ r: 2.5 }} connectNulls />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
            <Card>
              <CardHeader title="Favorable % heatmap" subtitle="Dimension × quarter" icon={LayoutDashboard} />
              <div className="overflow-x-auto p-4">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500">
                      <th className="px-2 py-1.5 text-left font-medium">Dimension</th>
                      {dates.map((d) => (
                        <th key={d} className="px-2 py-1.5 font-medium">{fmtQuarter(d)}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dimensions.map((dim) => (
                      <tr key={dim}>
                        <td className="whitespace-nowrap px-2 py-1.5 font-medium">{dim}</td>
                        {dates.map((d) => {
                          const row = byKey.get(`${dim}|${d}`)
                          return (
                            <td key={d} className="px-1 py-1 text-center tabular-nums">
                              <span className="block rounded-md px-1.5 py-1" style={{ background: heatColor(row?.Favorable_Percent ?? null) }} title={row ? `n=${row.Responses} of ${row.Eligible_Employees}` : 'suppressed'}>
                                {row?.Favorable_Percent?.toFixed(0) ?? '—'}
                              </span>
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
            <Card>
              <CardHeader title="Ask Echo about this team" icon={Sparkles} />
              <div className="space-y-2 p-4">
                {[
                  `What do this quarter's recognition metrics and comments suggest?`,
                  `Show Recognition over eight quarters by team.`,
                  `Which survey dimension declined most recently, and what do comments say about it?`,
                ].map((q) => (
                  <Link key={q} to={`/console?q=${encodeURIComponent(q)}&manager=${manager}`} className="block rounded-xl border border-slate-200 p-3 text-sm transition hover:border-indigo-300 hover:bg-indigo-50/40 dark:border-slate-700 dark:hover:border-indigo-500 dark:hover:bg-indigo-500/5">
                    {q}
                  </Link>
                ))}
                {enps.length > 0 && (
                  <p className="pt-2 text-xs text-slate-500">
                    Latest eNPS: <span className="font-semibold text-slate-700 dark:text-slate-200">{enps.at(-1)?.eNPS_Score ?? '—'}</span> ({fmtQuarter(enps.at(-1)!.Survey_Date)})
                  </p>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}
    </>
  )
}
