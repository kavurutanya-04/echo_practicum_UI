import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Badge, Card, CardHeader } from '../ui'

const LABELS = [
  { key: 'positive', color: '#10b981' },
  { key: 'neutral', color: '#94a3b8' },
  { key: 'mixed', color: '#d97706' },
  { key: 'negative', color: '#e11d48' },
  { key: 'indeterminate', color: '#cbd5e1' },
]

type SentimentReport = {
  citation_id: string
  dimension: string | null
  eligible_comments: number
  classified_comments: number
  rows: Record<string, string | number>[]
  suppressed_groups: number
  examples: { citation_id: string; label: string; excerpt?: string; explanation?: string }[]
  note: string
}

/** Stacked percentages per team/date from Vanilla's systematic sentiment classification. */
export default function Sentiment({ reports }: { reports: Record<string, unknown> }) {
  return (
    <div className="space-y-6">
      {Object.values(reports as Record<string, SentimentReport>).map((report) => {
        const data = report.rows.map((row) => ({
          name: `${row.Team} · ${row.Survey_Date}`,
          ...Object.fromEntries(LABELS.map((l) => [l.key, row[`${l.key}_percent`] ?? 0])),
          n: row.Eligible_Comments,
        }))
        return (
          <Card key={report.citation_id}>
            <CardHeader
              title={`Comment sentiment${report.dimension ? ` · ${report.dimension}` : ''}`}
              subtitle={`${report.classified_comments} of ${report.eligible_comments} eligible comments classified · ${report.suppressed_groups} small groups suppressed`}
              action={<Badge tone="amber">provisional labels</Badge>}
            />
            <div className="p-4 text-slate-400" style={{ height: Math.max(220, data.length * 34 + 80) }}>
              <ResponsiveContainer>
                <BarChart data={data} layout="vertical" margin={{ left: 24, right: 16 }}>
                  <CartesianGrid strokeOpacity={0.15} horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} unit="%" stroke="currentColor" fontSize={11} />
                  <YAxis type="category" dataKey="name" width={170} stroke="currentColor" fontSize={11} />
                  <Tooltip formatter={(v) => `${v}%`} contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {LABELS.map((l) => (
                    <Bar key={l.key} dataKey={l.key} stackId="s" fill={l.color} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
            {report.examples?.length > 0 && (
              <div className="grid gap-3 border-t border-slate-100 p-4 md:grid-cols-2 dark:border-slate-800">
                {report.examples.map((example) => (
                  <div key={example.citation_id + example.label} className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/50">
                    <div className="mb-1 flex gap-1.5">
                      <Badge tone={example.label === 'positive' ? 'green' : example.label === 'negative' ? 'red' : 'amber'}>{example.label}</Badge>
                      <Badge>{example.citation_id}</Badge>
                    </div>
                    {example.excerpt && <p>“{example.excerpt}”</p>}
                    {example.explanation && <p className="mt-1 text-xs text-slate-500">{example.explanation}</p>}
                  </div>
                ))}
              </div>
            )}
            <p className="border-t border-slate-100 px-4 py-3 text-xs text-slate-500 dark:border-slate-800">{report.note}</p>
          </Card>
        )
      })}
    </div>
  )
}
