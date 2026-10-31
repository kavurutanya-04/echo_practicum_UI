import { BarChart3, Check, ChevronDown, Download, ExternalLink, FileImage, Loader2, X } from 'lucide-react'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, isSql, type Artifact, type ChartSpec, type SqlEvidence } from '../../lib/api'
import { SERIES_COLORS } from '../../lib/agents'
import { Card, CardHeader, Empty } from '../ui'

/** Pivot evidence rows into recharts' wide format: one object per x value, one key per series. */
function pivot(spec: ChartSpec, rows: Record<string, unknown>[]) {
  const series = new Set<string>()
  const byX = new Map<string, Record<string, unknown>>()
  for (const row of rows) {
    const x = String(row[spec.x])
    const name = spec.series ? String(row[spec.series]) : spec.y_label || spec.y
    series.add(name)
    const entry = byX.get(x) ?? { [spec.x]: x }
    entry[name] = row[spec.y]
    if (spec.denominator) entry[`${name}__n`] = row[spec.denominator]
    byX.set(x, entry)
  }
  return { data: [...byX.values()], series: [...series] }
}

const color = (i: number) => SERIES_COLORS[i % SERIES_COLORS.length]

/** A line chart's point, each in the next pastel so a single line still reads in several colours. */
function PastelDot({ cx, cy, index }: { cx?: number; cy?: number; index?: number }) {
  if (cx === undefined || cy === undefined) return null
  return <circle cx={cx} cy={cy} r={5} fill={color(index ?? 0)} stroke="white" strokeWidth={2} />
}

type ExportTool = 'powerbi' | 'tableau' | 'excel'

/** What each export gives, how to open it and where it comes from. */
const EXPORTS: Record<ExportTool, { label: string; file: string; url: (run: string, source: string) => string; about: string; needs: string; steps: string[] }> = {
  powerbi: {
    label: 'Power BI',
    file: 'a zip file',
    url: api.chartPowerBiUrl,
    about: 'Echo builds a Power BI report for you: this chart in the same colours, with the question, what Echo found, why it matters, what to do first and the numbers behind it, on one page.',
    needs: 'Needs Power BI Desktop (September 2026 or newer) on Windows.',
    steps: ['In your Downloads folder, right-click it and choose Extract All.', 'Double-click the .pbip file inside. Power BI Desktop opens on the chart. If it looks empty, choose Refresh once.'],
  },
  tableau: {
    label: 'Tableau',
    file: 'a .twbx file',
    url: api.chartTableauUrl,
    about: 'Echo builds a Tableau workbook for you: this chart in the same colours, with the question, what Echo found, why it matters and what to do first in the caption underneath.',
    needs: 'Needs Tableau Desktop or Tableau Public, version 2026.1 or newer.',
    steps: ['Double-click it in your Downloads folder. Tableau opens on the chart.', 'The description is in the caption under the chart (Worksheet menu, Show Caption, if it is hidden).'],
  },
  excel: {
    label: 'Excel',
    file: 'an .xlsx file',
    url: api.chartExcelUrl,
    about: 'Echo builds an Excel workbook for you: this chart as a real Excel chart in the same colours, with the question, what Echo found, why it matters and what to do first, and the numbers on their own sheet.',
    needs: 'Opens in Excel (2016 or newer) and most spreadsheet apps.',
    steps: ['Open it from your Downloads folder.', 'The chart and its description are on the first sheet; the numbers are on the Numbers sheet.'],
  },
}

/** Downloads a file and reports a readable error instead of saving an error page. */
async function download(url: string) {
  const response = await fetch(url)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail || `The export failed (${response.status}).`)
  }
  const name = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') ?? '')?.[1] ?? 'Echo chart'
  const link = document.createElement('a')
  link.href = URL.createObjectURL(await response.blob())
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(link.href), 10_000)
}

/** Asks before handing a chart to Power BI, Tableau or Excel: a file that opens straight to this chart with its description. */
function ExportDialog({ spec, runId, rows, onClose }: { spec: ChartSpec; runId: string; rows: number; onClose: () => void }) {
  const [tool, setTool] = useState<ExportTool>(() => {
    try {
      const saved = localStorage.getItem('echo-export-tool')
      return saved === 'tableau' || saved === 'excel' ? saved : 'powerbi'
    } catch {
      return 'powerbi'
    }
  })
  const [state, setState] = useState<'ask' | 'working' | 'done'>('ask')
  const [error, setError] = useState('')
  const choice = EXPORTS[tool]
  const columns = [spec.x, spec.series, spec.y, spec.denominator].filter(Boolean).join(', ')

  function pick(next: ExportTool) {
    setTool(next)
    setError('')
    try {
      localStorage.setItem('echo-export-tool', next)
    } catch {
      /* storage unavailable */
    }
  }

  async function start() {
    setState('working')
    setError('')
    try {
      await download(choice.url(runId, spec.source_id))
      setState('done')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setState('ask')
    }
  }

  return (
    // Clicks and keys inside the dialog must not reach the chart behind it, which would reopen the dialog.
    <div
      className="fixed inset-0 z-[60] grid cursor-default place-items-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Open this chart in another tool"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => {
        e.stopPropagation()
        if (e.key === 'Escape') onClose()
      }}
    >
      <div className="absolute inset-0 bg-slate-950/30 backdrop-blur-[1px]" onClick={onClose} />
      <div className="slide-in relative w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl dark:bg-slate-900">
        <button onClick={onClose} className="absolute right-3 top-3 rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close">
          <X className="size-4" />
        </button>
        <div className="flex items-center gap-3 pr-8">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
            <BarChart3 className="size-5" />
          </span>
          <div className="min-w-0">
            <div className="text-base font-semibold">Open this chart in…</div>
            <div className="truncate text-xs text-slate-500">{spec.title}</div>
          </div>
        </div>
        <label className="mt-4 block text-xs font-medium text-slate-500 dark:text-slate-400" htmlFor="echo-export-tool">
          Open in
        </label>
        <div className="relative mt-1">
          <select
            id="echo-export-tool"
            value={tool}
            disabled={state !== 'ask'}
            onChange={(e) => pick(e.target.value as ExportTool)}
            className="w-full appearance-none rounded-xl border border-slate-200 bg-white py-2 pl-3 pr-9 text-sm font-medium text-slate-800 outline-none transition focus:border-indigo-400 focus:ring-4 focus:ring-indigo-400/15 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          >
            {(Object.keys(EXPORTS) as ExportTool[]).map((key) => (
              <option key={key} value={key}>
                {EXPORTS[key].label}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
        </div>
        {state !== 'done' ? (
          <>
            <p className="mt-4 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{choice.about}</p>
            <ul className="mt-3 space-y-1 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
              <li>
                Includes {rows} row{rows === 1 ? '' : 's'}: {columns}
              </li>
              <li>Only your team's numbers for this chart. No survey comments.</li>
              <li>Works offline: the numbers are saved inside the file. {choice.needs}</li>
            </ul>
            {error && <p className="mt-3 rounded-xl bg-rose-50 p-3 text-xs text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">{error}</p>}
          </>
        ) : (
          <ol className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
            <li className="flex gap-2">
              <Check className="mt-0.5 size-4 shrink-0 text-indigo-600" /> The {choice.label} file is downloading as {choice.file}.
            </li>
            {choice.steps.map((step, i) => (
              <li key={step} className="flex gap-2">
                <span className="w-4 shrink-0 text-center font-semibold text-indigo-600">{i + 2}</span> {step}
              </li>
            ))}
          </ol>
        )}
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <a
            href={api.chartCsvUrl(runId, spec.source_id)}
            download
            className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Download className="size-4" /> Data only (CSV)
          </a>
          {state !== 'done' ? (
            <button
              onClick={start}
              disabled={state === 'working'}
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-70"
            >
              {state === 'working' ? <Loader2 className="size-4 animate-spin" /> : <ExternalLink className="size-4" />} Open in {choice.label}
            </button>
          ) : (
            <button onClick={onClose} className="rounded-xl bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700">
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function EvidenceChart({ spec, evidence, height = 300, runId }: { spec: ChartSpec; evidence: SqlEvidence; height?: number; runId?: string }) {
  const { data, series } = pivot(spec, evidence.rows)
  const single = series.length === 1
  const [asking, setAsking] = useState(false)
  const axis = { stroke: 'currentColor', fontSize: 11, tickLine: false, axisLine: false }
  const Chart = spec.kind === 'bar' ? BarChart : LineChart
  // With a run to export from, clicking the chart offers to open it in Power BI, Tableau or Excel.
  const clickable = runId
    ? {
        role: 'button',
        tabIndex: 0,
        title: 'Click to open this chart in Power BI, Tableau or Excel',
        'aria-label': `${spec.title}. Open in Power BI, Tableau or Excel`,
        onClick: () => setAsking(true),
        onKeyDown: (e: React.KeyboardEvent) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setAsking(true)),
      }
    : {}
  return (
    <div className={runId ? 'group relative cursor-pointer rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-indigo-400' : undefined} {...clickable}>
      {runId && (
        <span className="pointer-events-none absolute right-2 top-0 z-10 inline-flex items-center gap-1 rounded-full bg-white/90 px-2 py-0.5 text-[11px] font-medium text-slate-500 ring-1 ring-slate-200 transition group-hover:text-indigo-700 group-hover:ring-indigo-300 dark:bg-slate-900/90 dark:ring-slate-700">
          <ExternalLink className="size-3" /> Open in…
        </span>
      )}
      {asking && runId && <ExportDialog spec={spec} runId={runId} rows={evidence.rows.length} onClose={() => setAsking(false)} />}
    <div className="text-slate-400" style={{ height }}>
      <ResponsiveContainer>
        <Chart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.15} vertical={false} />
          <XAxis dataKey={spec.x} {...axis} />
          {/* Bars start at zero so their heights compare honestly; lines may zoom to their range. */}
          <YAxis {...axis} width={44} domain={spec.kind === 'bar' ? [(min: number) => Math.min(0, min), 'auto'] : ['auto', 'auto']} />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: '1px solid var(--color-slate-200)', fontSize: 12 }}
            cursor={{ fill: 'var(--color-slate-100)', opacity: 0.6 }}
            formatter={(value, name, item) => {
              const n = (item?.payload as Record<string, unknown>)?.[`${name}__n`]
              return [`${value}${spec.unit ? ` ${spec.unit}` : ''}${n !== undefined ? ` (n=${n})` : ''}`, name]
            }}
          />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
          {series.map((name, i) =>
            spec.kind === 'bar' ? (
              <Bar key={name} dataKey={name} fill={color(i)} radius={[8, 8, 0, 0]} maxBarSize={56}>
                {/* One series: every bar gets its own pastel. Several series: one pastel per series. */}
                {single && data.map((_, j) => <Cell key={j} fill={color(j)} />)}
              </Bar>
            ) : (
              <Line
                key={name}
                dataKey={name}
                type="monotone"
                stroke={color(i)}
                strokeWidth={3}
                dot={single ? (props) => <PastelDot key={props.index} {...props} /> : { r: 3.5, fill: color(i), stroke: 'white', strokeWidth: 1.5 }}
                activeDot={{ r: 6, stroke: 'white', strokeWidth: 2 }}
              />
            ),
          )}
        </Chart>
      </ResponsiveContainer>
    </div>
    </div>
  )
}

export default function Charts({ artifact, runId }: { artifact: Artifact }  & { runId: string }) {
  const charts = artifact.visualization?.charts ?? []
  const files = artifact.visualization?.files ?? []
  const evidence = [...(artifact.evidence ?? []), ...(artifact.delegations ?? []).flatMap((d) => d.evidence ?? [])].filter(isSql)

  if (!charts.length)
    return (
      <Empty icon={BarChart3} title="No chart for this answer">
        {artifact.visualization?.reason || 'Lime only draws charts that are directly supported by numeric evidence.'}
      </Empty>
    )

  return (
    <div className="space-y-6">
      {artifact.visualization?.reason && <p className="text-sm text-slate-500">Lime: {artifact.visualization.reason}</p>}
      {charts.map((spec, i) => {
        const source = evidence.find((e) => e.citation_id === spec.source_id)
        const file = files.find((f) => f.source_id === spec.source_id) ?? files[i]
        return (
          <Card key={i}>
            <CardHeader
              title={spec.title}
              subtitle={`${spec.y_label}${spec.unit ? ` (${spec.unit})` : ''} by ${spec.x_label}${spec.denominator ? ` · denominator: ${spec.denominator}` : ''} · source ${spec.source_id}`}
              icon={BarChart3}
              action={
                file && (
                  <div className="flex gap-1">
                    <a className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" href={api.fileUrl(runId, file.svg)} target="_blank" rel="noreferrer">
                      <FileImage className="size-3.5" /> SVG
                    </a>
                    <a className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" href={api.fileUrl(runId, file.csv)} download>
                      <Download className="size-3.5" /> CSV
                    </a>
                  </div>
                )
              }
            />
            <div className="p-4">
              {source ? (
                <EvidenceChart spec={spec} evidence={source} runId={runId} />
              ) : file ? (
                <img src={api.fileUrl(runId, file.svg)} alt={spec.title} className="mx-auto max-h-96 rounded-lg bg-white" />
              ) : (
                <p className="text-sm text-slate-500">The cited source rows are not in this artifact.</p>
              )}
            </div>
          </Card>
        )
      })}
    </div>
  )
}
