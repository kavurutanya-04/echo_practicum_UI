import clsx from 'clsx'
import { AlertTriangle, ChevronDown, History, Loader2, MessagesSquare, ShieldAlert, ShieldCheck, Table2, Workflow } from 'lucide-react'
import { Fragment, useState } from 'react'
import { EvidenceChart } from '../components/run/Charts'
import { SqlBlock } from '../components/run/Evidence'
import { isSql, type Artifact, type Made, type RunMeta, type SqlEvidence } from '../lib/api'

const CITATION = /\s*\[([A-Za-z]+\d*(?::[A-Za-z0-9_-]+)?)\]/g

function friendlyFailure(meta: RunMeta) {
  return meta.state === 'cancelled'
    ? 'You stopped this answer.'
    : "Echo couldn't finish this answer. This is usually a temporary model limit or outage — try again later, or try demo mode."
}

/** Answer text with numbered source markers; data sources expand inline, comments stay redacted. */
function SourcedText({ text, sources, onOpen, onOpenPulse }: { text: string; sources: Map<string, SqlEvidence | null>; onOpen: (id: string) => void; onOpenPulse: () => void }) {
  const parts: (string | string)[] = []
  const ids: string[] = []
  let last = 0
  for (const match of text.matchAll(CITATION)) {
    parts.push(text.slice(last, match.index))
    ids.push(match[1])
    parts.push(`\u0000${match[1]}`)
    last = (match.index ?? 0) + match[0].length
  }
  parts.push(text.slice(last))
  return (
    <>
      {parts.map((part, index) => {
        if (!part.startsWith('\u0000')) return <Fragment key={index}>{part}</Fragment>
        const id = part.slice(1)
        const data = sources.get(id)
        return data ? (
          <button
            key={index}
            onClick={() => onOpen(id)}
            className="mx-0.5 inline-flex translate-y-[-1px] items-center gap-1 rounded-md bg-indigo-50 px-1.5 py-0.5 align-middle text-[11px] font-medium text-indigo-700 ring-1 ring-inset ring-indigo-600/20 hover:bg-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/30"
            title="Show the data behind this"
          >
            <Table2 className="size-3" /> data
          </button>
        ) : (
          <button
            key={index}
            onClick={onOpenPulse}
            className="mx-0.5 inline-flex translate-y-[-1px] items-center gap-1 rounded-md bg-slate-100 px-1.5 py-0.5 align-middle text-[11px] text-slate-500 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
            title="Based on team survey responses — see the summary of what your team is saying"
          >
            <MessagesSquare className="size-3" /> survey
          </button>
        )
      })}
    </>
  )
}

export function PendingBubble({ status }: { status: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
      <Loader2 className="size-4 animate-spin text-indigo-500" />
      {status}
    </div>
  )
}

function describeMade(made: Made) {
  const parts = ['Original planned the answer']
  if (made.queries) parts.push(`Cherry ran ${made.queries} data quer${made.queries === 1 ? 'y' : 'ies'}`)
  if (made.survey_sources || made.sentiment_runs) parts.push('Vanilla reviewed survey responses')
  if (made.charts) parts.push(`Lime drew ${made.charts} chart${made.charts === 1 ? '' : 's'}`)
  else parts.push('Lime decided no chart was needed')
  parts.push(`ZeroSugar checked ${made.drafts_checked > 1 ? `${made.drafts_checked} drafts` : 'the answer'}${made.findings_checked ? ` and ${made.findings_checked} finding${made.findings_checked === 1 ? '' : 's'}` : ''}`)
  return parts.join(' · ')
}

export default function AnswerBubble({ meta, artifact, onOpenPulse }: { meta: RunMeta; artifact: Artifact | null; onOpenPulse: () => void }) {
  const [openSource, setOpenSource] = useState<string | null>(null)
  const [notesOpen, setNotesOpen] = useState(false)
  const [madeOpen, setMadeOpen] = useState(false)

  if (!artifact || meta.state === 'failed' || meta.state === 'cancelled' || artifact.status === 'failed') {
    return (
      <div className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" />
        {friendlyFailure(meta)}
      </div>
    )
  }

  const allEvidence = [...(artifact.evidence ?? []), ...(artifact.delegations ?? []).flatMap((d) => d.evidence ?? [])]
  const sources = new Map<string, SqlEvidence | null>()
  for (const item of allEvidence) if (!sources.has(item.citation_id)) sources.set(item.citation_id, isSql(item) ? item : null)
  const chart = artifact.visualization?.charts?.[0]
  const chartSource = chart ? sources.get(chart.source_id) : null
  const verified = artifact.verification?.decision === 'accept'
  const commentCount = allEvidence.filter((e) => !isSql(e) && (e as { source?: string }).source === 'HR_survey_comments').length
  const opened = openSource ? sources.get(openSource) : null

  return (
    <div className="space-y-4">
      {meta.mode === 'demo' && (
        <div className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
          Demo mode: no saved answer exists for this question yet, so this is Echo's scripted sample answer. Switch to Live AI for a real answer.
        </div>
      )}
      {meta.mode === 'offline' && artifact.status !== 'needs_clarification' && (
        <div className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Offline demo: numbers are computed directly from your team's data; the wording is a fixed template, not AI.
        </div>
      )}
      {meta.mode === 'replay' && (
        <div className="flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs text-indigo-800 dark:bg-indigo-500/10 dark:text-indigo-300">
          <History className="size-3.5" /> Saved answer from a live run{meta.recorded_at ? ` on ${new Date(meta.recorded_at).toLocaleDateString()}` : ''} — replayed without using the AI.
        </div>
      )}
      <div className="text-[15px] leading-7">
        {artifact.answer.split(/\n{2,}/).map((paragraph, i) => (
          <p key={i} className="mb-2.5 last:mb-0">
            <SourcedText text={paragraph} sources={sources} onOpen={(id) => setOpenSource(openSource === id ? null : id)} onOpenPulse={onOpenPulse} />
          </p>
        ))}
      </div>

      {opened && (
        <div className="slide-in rounded-xl border border-slate-200 p-3 dark:border-slate-700">
          <div className="mb-2 flex items-center justify-between text-xs font-medium text-slate-500">
            Data behind this answer
            <button className="hover:text-slate-800 dark:hover:text-slate-200" onClick={() => setOpenSource(null)}>
              Hide
            </button>
          </div>
          <SqlBlock evidence={opened} />
        </div>
      )}

      {chart && chartSource && (
        <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
          <div className="mb-1 text-sm font-medium">{chart.title}</div>
          <div className="mb-2 text-xs text-slate-500">
            {chart.y_label}
            {chart.unit ? ` (${chart.unit})` : ''} by {chart.x_label}
          </div>
          <EvidenceChart spec={chart} evidence={chartSource} height={240} />
        </div>
      )}

      {artifact.status !== 'needs_clarification' && <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          className={clsx(
            'inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium ring-1 ring-inset',
            verified
              ? 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-400/20'
              : 'bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-400/20',
          )}
        >
          {verified ? <ShieldCheck className="size-3.5" /> : <ShieldAlert className="size-3.5" />}
          {verified ? 'Checked by ZeroSugar' : 'Not fully verified'}
        </span>
        {commentCount > 0 && (
          <button onClick={onOpenPulse} className="inline-flex items-center gap-1 text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400">
            <MessagesSquare className="size-3" /> Draws on team survey responses · see what your team is saying
          </button>
        )}
        {artifact.made && (
          <button onClick={() => setMadeOpen(!madeOpen)} className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
            <Workflow className="size-3" /> How this answer was made <ChevronDown className={clsx('size-3.5 transition', madeOpen && 'rotate-180')} />
          </button>
        )}
        {artifact.limitations?.length > 0 && (
          <button onClick={() => setNotesOpen(!notesOpen)} className="ml-auto inline-flex items-center gap-1 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
            Notes & limitations <ChevronDown className={clsx('size-3.5 transition', notesOpen && 'rotate-180')} />
          </button>
        )}
      </div>}
      {madeOpen && artifact.made && <p className="slide-in rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800/50 dark:text-slate-300">{describeMade(artifact.made)}.</p>}
      {notesOpen && (
        <ul className="slide-in space-y-1 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800/50 dark:text-slate-300">
          {artifact.limitations.map((note, i) => (
            <li key={i}>• {note}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
