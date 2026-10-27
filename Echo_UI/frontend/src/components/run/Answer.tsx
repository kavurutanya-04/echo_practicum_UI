import { AlertCircle, CheckCircle2, HelpCircle, Lightbulb, ListChecks } from 'lucide-react'
import { Fragment, useState } from 'react'
import type { Artifact, Evidence } from '../../lib/api'
import { STATE_TONE } from '../../lib/format'
import { Badge } from '../ui'
import { EvidenceDrawer } from './Evidence'

const CITATION = /\[([A-Za-z]+\d*(?::[A-Za-z0-9_-]+)?)\]/g

/** Render text with [SQL1] / [survey:CMT123] citations as clickable chips. */
export function CitedText({ text, onCite, known }: { text: string; onCite: (id: string) => void; known: Set<string> }) {
  const parts: (string | { id: string })[] = []
  let last = 0
  for (const match of text.matchAll(CITATION)) {
    parts.push(text.slice(last, match.index))
    parts.push({ id: match[1] })
    last = (match.index ?? 0) + match[0].length
  }
  parts.push(text.slice(last))
  return (
    <>
      {parts.map((part, index) =>
        typeof part === 'string' ? (
          <Fragment key={index}>{part}</Fragment>
        ) : (
          <button
            key={index}
            onClick={() => onCite(part.id)}
            disabled={!known.has(part.id)}
            className="mx-0.5 inline-flex translate-y-[-1px] items-center rounded-md bg-indigo-50 px-1.5 py-0.5 align-middle font-mono text-[11px] font-medium text-indigo-700 ring-1 ring-inset ring-indigo-600/20 transition hover:bg-indigo-100 disabled:opacity-50 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/30"
            title={known.has(part.id) ? 'Open source' : 'Source not in this artifact'}
          >
            {part.id}
          </button>
        ),
      )}
    </>
  )
}

function List({ icon: Icon, title, items, tone }: { icon: typeof Lightbulb; title: string; items: string[]; tone: string }) {
  if (!items?.length) return null
  return (
    <div>
      <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
        <Icon className={`size-4 ${tone}`} /> {title}
      </h4>
      <ul className="space-y-1.5 text-sm text-slate-600 dark:text-slate-300">
        {items.map((item, index) => (
          <li key={index} className="flex gap-2">
            <span className="mt-2 size-1 shrink-0 rounded-full bg-slate-400" /> {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Answer({ artifact }: { artifact: Artifact }) {
  const [open, setOpen] = useState<Evidence | null>(null)
  const index = new Map<string, Evidence>()
  for (const item of artifact.evidence ?? []) index.set(item.citation_id, item)
  for (const delegation of artifact.delegations ?? []) for (const item of delegation.evidence ?? []) if (!index.has(item.citation_id)) index.set(item.citation_id, item)
  const known = new Set(index.keys())
  const cite = (id: string) => setOpen(index.get(id) ?? null)

  return (
    <div className="space-y-8">
      <div className="text-[15px] leading-7">
        {artifact.answer.split(/\n{2,}/).map((paragraph, i) => (
          <p key={i} className="mb-3 last:mb-0">
            <CitedText text={paragraph} onCite={cite} known={known} />
          </p>
        ))}
      </div>

      {artifact.findings?.length > 0 && (
        <div>
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <ListChecks className="size-4 text-indigo-500" /> Findings checked by ZeroSugar
          </h4>
          <div className="space-y-2">
            {artifact.findings.map((finding) => (
              <div key={finding.finding_id} className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-800">
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="font-mono text-xs text-slate-500">{finding.finding_id}</span>
                  <Badge tone={STATE_TONE[finding.status] ?? 'amber'}>
                    {finding.status === 'supported' ? <CheckCircle2 className="size-3" /> : <AlertCircle className="size-3" />}
                    {finding.status}
                  </Badge>
                </div>
                <p className="leading-relaxed">
                  <CitedText text={finding.text} onCite={cite} known={known} />
                </p>
                {finding.reason && <p className="mt-1.5 text-xs text-slate-500">{finding.reason}</p>}
                {!!finding.assertions?.length && (
                  <details className="mt-2 text-xs">
                    <summary className="cursor-pointer text-slate-500">Evidence checks ({finding.assertions.length})</summary>
                    <ul className="mt-2 space-y-2">
                      {finding.assertions.map((assertion, index) => (
                        <li key={assertion.assertion_id ?? index} className="border-l-2 border-slate-200 pl-2 dark:border-slate-700">
                          <span className="font-medium">{assertion.assessment.replaceAll('_', ' ')}: </span>
                          <CitedText text={assertion.claim} onCite={cite} known={known} />
                          <p className="mt-1 text-slate-500">{assertion.reason}</p>
                          <p className="text-slate-500">Sources: {assertion.citation_ids.join(', ') || 'None cited'}</p>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        <List icon={AlertCircle} title="Limitations" items={artifact.limitations} tone="text-amber-500" />
        <List icon={Lightbulb} title="Suggested next steps" items={artifact.next_steps} tone="text-emerald-500" />
        <List icon={HelpCircle} title="Clarifying questions" items={artifact.clarification_questions} tone="text-indigo-500" />
      </div>

      <EvidenceDrawer evidence={open} onClose={() => setOpen(null)} />
    </div>
  )
}
