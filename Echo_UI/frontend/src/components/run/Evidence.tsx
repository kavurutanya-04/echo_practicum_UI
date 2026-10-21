import { Check, Copy, Database, Download, MessageSquareQuote, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { isSql, isText, type Evidence, type SqlEvidence, type TextEvidence } from '../../lib/api'
import { fmtNumber } from '../../lib/format'
import { Badge, Button } from '../ui'

function downloadCsv(name: string, rows: Record<string, unknown>[]) {
  if (!rows.length) return
  const columns = Object.keys(rows[0])
  const escape = (value: unknown) => `"${String(value ?? '').replace(/"/g, '""')}"`
  const body = [columns.map(escape).join(','), ...rows.map((row) => columns.map((c) => escape(row[c])).join(','))].join('\n')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([body], { type: 'text/csv' }))
  link.download = `${name}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

export function SqlBlock({ evidence }: { evidence: SqlEvidence }) {
  const [copied, setCopied] = useState(false)
  const [all, setAll] = useState(false)
  const rows = all ? evidence.rows : evidence.rows.slice(0, 12)
  const columns = evidence.rows.length ? Object.keys(evidence.rows[0]) : []
  return (
    <div className="space-y-3">
      <div className="relative">
        <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 pr-12 font-mono text-[12px] leading-relaxed text-slate-100">{evidence.sql}</pre>
        <button
          className="absolute right-2 top-2 rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
          aria-label="Copy SQL"
          onClick={() => {
            navigator.clipboard?.writeText(evidence.sql)
            setCopied(true)
            setTimeout(() => setCopied(false), 1200)
          }}
        >
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </button>
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          {evidence.rows.length} row{evidence.rows.length === 1 ? '' : 's'} returned{evidence.truncated ? ' (truncated by Echo)' : ''} · produced by {evidence.producer}
        </span>
        <Button variant="ghost" icon={Download} className="!px-2 !py-1 text-xs" onClick={() => downloadCsv(evidence.citation_id, evidence.rows)}>
          CSV
        </Button>
      </div>
      {columns.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
              <tr>
                {columns.map((column) => (
                  <th key={column} className="whitespace-nowrap px-3 py-2 font-medium">
                    {column.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {rows.map((row, index) => (
                <tr key={index} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30">
                  {columns.map((column) => (
                    <td key={column} className="whitespace-nowrap px-3 py-1.5 tabular-nums">
                      {fmtNumber(row[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {evidence.rows.length > 12 && (
        <button className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400" onClick={() => setAll(!all)}>
          {all ? 'Show fewer rows' : `Show all ${evidence.rows.length} rows`}
        </button>
      )}
    </div>
  )
}

export function CommentCard({ evidence }: { evidence: TextEvidence }) {
  const [prompt, ...answer] = evidence.text.split('\n')
  return (
    <figure className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      {answer.length > 0 && <figcaption className="mb-1.5 text-xs text-slate-500">{prompt}</figcaption>}
      <blockquote className="text-sm leading-relaxed">“{answer.length ? answer.join(' ') : prompt}”</blockquote>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge tone="blue">{evidence.citation_id}</Badge>
        {evidence.dimension && <Badge>{evidence.dimension}</Badge>}
        {evidence.team && <Badge>{evidence.team}</Badge>}
        {evidence.date && <Badge>{evidence.date}</Badge>}
        {evidence.anonymous && <Badge tone="green">anonymous</Badge>}
      </div>
    </figure>
  )
}

export function EvidenceItem({ evidence }: { evidence: Evidence }) {
  if (isSql(evidence)) return <SqlBlock evidence={evidence} />
  if (isText(evidence)) return <CommentCard evidence={evidence} />
  return <pre className="overflow-x-auto rounded-xl bg-slate-100 p-3 font-mono text-xs dark:bg-slate-800">{JSON.stringify(evidence, null, 2)}</pre>
}

/** All evidence grouped by kind. */
export default function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  const sql = evidence.filter(isSql)
  const text = evidence.filter(isText)
  const other = evidence.filter((e) => !isSql(e) && !isText(e))
  return (
    <div className="space-y-8">
      {sql.length > 0 && (
        <section className="space-y-4">
          <h4 className="flex items-center gap-2 text-sm font-semibold">
            <Database className="size-4 text-[var(--color-cherry)]" /> SQL evidence ({sql.length})
          </h4>
          {sql.map((item) => (
            <div key={item.citation_id} id={`ev-${item.citation_id}`}>
              <Badge tone="blue" className="mb-2">{item.citation_id}</Badge>
              <SqlBlock evidence={item} />
            </div>
          ))}
        </section>
      )}
      {text.length > 0 && (
        <section className="space-y-3">
          <h4 className="flex items-center gap-2 text-sm font-semibold">
            <MessageSquareQuote className="size-4 text-[var(--color-vanilla)]" /> Anonymous comments ({text.length})
          </h4>
          <div className="grid gap-3 md:grid-cols-2">
            {text.map((item) => (
              <CommentCard key={item.citation_id} evidence={item} />
            ))}
          </div>
        </section>
      )}
      {other.map((item) => (
        <EvidenceItem key={item.citation_id} evidence={item} />
      ))}
    </div>
  )
}

/** Slide-over panel showing one cited source. */
export function EvidenceDrawer({ evidence, onClose }: { evidence: Evidence | null; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  if (!evidence) return null
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-950/30 backdrop-blur-[1px]" onClick={onClose} />
      <aside className="slide-in absolute inset-y-0 right-0 flex w-full max-w-xl flex-col bg-white shadow-2xl dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <div>
            <div className="text-xs text-slate-500">Cited source</div>
            <div className="font-mono text-sm font-semibold">{evidence.citation_id}</div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close">
            <X className="size-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          <EvidenceItem evidence={evidence} />
        </div>
      </aside>
    </div>
  )
}
