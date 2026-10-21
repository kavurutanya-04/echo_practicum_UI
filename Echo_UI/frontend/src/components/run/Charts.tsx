import { BarChart3, Download, FileImage } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
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

export function EvidenceChart({ spec, evidence, height = 300 }: { spec: ChartSpec; evidence: SqlEvidence; height?: number }) {
  const { data, series } = pivot(spec, evidence.rows)
  const axis = { stroke: 'currentColor', fontSize: 11, tickLine: false, axisLine: false }
  const Chart = spec.kind === 'bar' ? BarChart : LineChart
  return (
    <div className="text-slate-400" style={{ height }}>
      <ResponsiveContainer>
        <Chart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.15} vertical={false} />
          <XAxis dataKey={spec.x} {...axis} />
          <YAxis {...axis} width={44} domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: '1px solid rgb(226 232 240)', fontSize: 12 }}
            formatter={(value, name, item) => {
              const n = (item?.payload as Record<string, unknown>)?.[`${name}__n`]
              return [`${value}${spec.unit ? ` ${spec.unit}` : ''}${n !== undefined ? ` (n=${n})` : ''}`, name]
            }}
          />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
          {series.map((name, i) =>
            spec.kind === 'bar' ? (
              <Bar key={name} dataKey={name} fill={SERIES_COLORS[i % SERIES_COLORS.length]} radius={[6, 6, 0, 0]} />
            ) : (
              <Line key={name} dataKey={name} type="linear" stroke={SERIES_COLORS[i % SERIES_COLORS.length]} strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            ),
          )}
        </Chart>
      </ResponsiveContainer>
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
                <EvidenceChart spec={spec} evidence={source} />
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
