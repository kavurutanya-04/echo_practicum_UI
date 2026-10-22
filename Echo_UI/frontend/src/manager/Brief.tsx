import clsx from 'clsx'
import { AlertTriangle, BellPlus, Check, ChevronDown, FileText, History, Loader2, MessagesSquare, PenLine, ShieldCheck, ShieldX, Table2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { EvidenceChart } from '../components/run/Charts'
import { SqlBlock } from '../components/run/Evidence'
import { AGENTS, type AgentName } from '../lib/agents'
import { isSql, type Artifact, type Example, type RunMeta, type SqlEvidence, type TriangleSide } from '../lib/api'
import { NEWSROOM } from './AgentStage'
import { SourcedText } from './AnswerBubble'

const agentColor = (name: AgentName) => AGENTS.find((a) => a.name === name)!.color

/** A card owned by one agent: their colour, name and newsroom role on top. */
function AgentCard({ agent, title, children, className, muted }: { agent: AgentName; title: string; children: ReactNode; className?: string; muted?: boolean }) {
  const meta = AGENTS.find((a) => a.name === agent)!
  return (
    <section
      className={clsx('rounded-2xl border bg-white p-5 shadow-sm dark:bg-slate-900', muted ? 'border-dashed border-slate-200 dark:border-slate-800' : 'border-slate-200 dark:border-slate-800', className)}
      style={{ borderTop: muted ? undefined : `3px solid ${meta.color}` }}
    >
      <div className="mb-3 flex items-center gap-2.5">
        <span className="grid size-7 place-items-center rounded-full text-white" style={{ background: meta.color }}>
          <meta.icon className="size-3.5" />
        </span>
        <div>
          <div className="text-sm font-semibold leading-tight">{title}</div>
          <div className="text-[11px] text-slate-500">
            {agent} · {NEWSROOM[agent].title}
          </div>
        </div>
      </div>
      {children}
    </section>
  )
}

const TONE = {
  good: 'text-emerald-600 dark:text-emerald-400',
  fair: 'text-amber-600 dark:text-amber-400',
  poor: 'text-rose-600 dark:text-rose-400',
  neutral: 'text-slate-900 dark:text-white',
}

function Side({ title, side }: { title: string; side: TriangleSide }) {
  return (
    <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/50">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        <span className="size-2 rounded-full" style={{ background: agentColor(side.agent as AgentName) }} /> {title}
      </div>
      <div className={clsx('mt-1 text-3xl font-semibold tracking-tight', TONE[side.tone])}>{side.value}</div>
      <div className="text-xs text-slate-500 dark:text-slate-400">{side.label}</div>
    </div>
  )
}

function draftNote(example: Example) {
  const first = example.name.split(' ')[0]
  const outcome = example.outcome.charAt(0).toLowerCase() + example.outcome.slice(1).replace(/\.$/, '')
  return `Hi ${first},\n\nI wanted to recognize the work you did for ${example.team_helped} on ${new Date(example.date + 'T00:00:00').toLocaleDateString(undefined, { month: 'long', day: 'numeric' })}. Because of it, ${outcome}. Helping another team like this matters, and I want to make sure it is seen.\n\nThank you.`
}

function DraftNoteDialog({ example, onClose }: { example: Example; onClose: () => void }) {
  const [text, setText] = useState(() => draftNote(example))
  const [copied, setCopied] = useState(false)
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div className="absolute inset-0 bg-slate-950/40" onClick={onClose} />
      <div className="slide-in relative w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl dark:bg-slate-900">
        <div className="flex items-center gap-2 text-base font-semibold">
          <PenLine className="size-4 text-indigo-500" /> Draft recognition note
        </div>
        <p className="mt-1 text-xs text-slate-500">A starting point from the work record. Edit it in your own words — Echo never sends anything.</p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={9}
          className="mt-3 w-full resize-y rounded-xl border border-slate-200 bg-white p-3 text-sm leading-relaxed outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-500/10 dark:border-slate-700 dark:bg-slate-950"
        />
        <div className="mt-3 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl px-3.5 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
            Close
          </button>
          <button
            onClick={() => {
              navigator.clipboard?.writeText(text)
              setCopied(true)
            }}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            {copied ? <Check className="size-4" /> : <FileText className="size-4" />} {copied ? 'Copied' : 'Copy note'}
          </button>
        </div>
      </div>
    </div>
  )
}

/** While the agents work, each card waits with its agent's live status. */
export function BriefPending({ activity }: { activity: Partial<Record<AgentName, string>> }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {(['Original', 'Cherry', 'Vanilla', 'ZeroSugar'] as AgentName[]).map((agent) => (
        <AgentCard key={agent} agent={agent} title={agent === 'Original' ? 'The brief' : agent === 'Cherry' ? 'The records' : agent === 'Vanilla' ? "The team's voice" : 'The fact-check'} muted>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="size-4 animate-spin" style={{ color: agentColor(agent) }} />
            {activity[agent] ?? 'Waiting for the editor…'}
          </div>
        </AgentCard>
      ))}
    </div>
  )
}

export default function Brief({
  meta,
  artifact,
  managerId,
  onOpenPulse,
  onTrack,
  tracked,
}: {
  meta: RunMeta
  artifact: Artifact | null
  managerId: string
  onOpenPulse: () => void
  onTrack: (items: NonNullable<Artifact['watch']>) => void
  tracked: boolean
}) {
  const [openSource, setOpenSource] = useState<string | null>(null)
  const [draft, setDraft] = useState<Example | null>(null)
  const [notesOpen, setNotesOpen] = useState(false)

  if (!artifact || meta.state === 'failed' || meta.state === 'cancelled' || artifact.status === 'failed') {
    return (
      <AgentCard agent="Original" title="The brief">
        <p className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" />
          {meta.state === 'cancelled' ? 'You stopped this investigation.' : "The newsroom couldn't finish this one — usually a temporary model limit. Try again later, or use Demo mode."}
        </p>
      </AgentCard>
    )
  }

  const declined = artifact.status === 'declined'
  const allEvidence = [...(artifact.evidence ?? []), ...(artifact.delegations ?? []).flatMap((d) => d.evidence ?? [])]
  const sources = new Map<string, SqlEvidence | null>()
  for (const item of allEvidence) if (!sources.has(item.citation_id)) sources.set(item.citation_id, isSql(item) ? item : null)
  const queries = [...sources.values()].filter((e): e is SqlEvidence => !!e && !e.sql.startsWith('--'))
  const chart = artifact.visualization?.charts?.[0]
  const chartSource = chart ? sources.get(chart.source_id) : null
  const verified = artifact.verification?.decision === 'accept'
  const opened = openSource ? sources.get(openSource) : null
  const made = artifact.made
  const modeNote = artifact.status === 'declined'
    ? 'Declined before any data was read'
    : meta.mode === 'offline'
      ? 'Offline demo · numbers computed from your data, wording is a fixed template'
      : meta.mode === 'replay'
        ? `Saved live answer${meta.recorded_at ? ` from ${new Date(meta.recorded_at).toLocaleDateString()}` : ''} · replayed without AI`
        : meta.mode === 'demo'
          ? "Scripted sample · not an answer to your question"
          : 'Live AI'

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        {meta.mode === 'replay' && <History className="size-3.5" />}
        <span>{modeNote}</span>
        <span>·</span>
        <span>
          {managerId} · {meta.start_date} → {meta.end_date}
        </span>
      </div>

      {declined ? (
        <>
          <AgentCard agent="Original" title="Echo declined this request">
            <p className="flex items-start gap-2 text-[15px] leading-7">
              <ShieldX className="mt-1 size-5 shrink-0 text-rose-500" />
              {artifact.answer}
            </p>
          </AgentCard>
          <AgentCard agent="ZeroSugar" title="Why">
            <p className="text-sm font-medium">{artifact.guardrail?.rule}</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{artifact.guardrail?.detail}</p>
            <ul className="mt-3 space-y-1.5 text-sm">
              {artifact.next_steps.map((step) => (
                <li key={step} className="flex gap-2">
                  <span className="text-indigo-500">→</span> {step}
                </li>
              ))}
            </ul>
            <button onClick={onOpenPulse} className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">
              <MessagesSquare className="size-4" /> Open Team pulse
            </button>
          </AgentCard>
        </>
      ) : (
        <>
          <AgentCard agent="Original" title="The brief">
            <div className="text-[15px] leading-7">
              {artifact.answer.split(/\n{2,}/).map((paragraph, i) => (
                <p key={i} className="mb-2 last:mb-0">
                  <SourcedText text={paragraph} sources={sources} onOpen={(id) => setOpenSource(openSource === id ? null : id)} onOpenPulse={onOpenPulse} />
                </p>
              ))}
            </div>
            {opened && (
              <div className="slide-in mt-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <div className="mb-2 flex items-center justify-between text-xs font-medium text-slate-500">
                  Data behind this
                  <button className="hover:text-slate-800 dark:hover:text-slate-200" onClick={() => setOpenSource(null)}>
                    Hide
                  </button>
                </div>
                <SqlBlock evidence={opened} />
              </div>
            )}
          </AgentCard>

          {artifact.triangle && (
            <section className={clsx('rounded-2xl border p-5', artifact.triangle.agreement === 'conflict' ? 'border-amber-300 bg-amber-50/50 dark:border-amber-500/30 dark:bg-amber-500/5' : 'border-emerald-200 bg-emerald-50/40 dark:border-emerald-500/20 dark:bg-emerald-500/5')}>
              <div className="mb-3 flex items-center justify-between gap-2">
                <div className="text-sm font-semibold">The evidence triangle</div>
                <span className={clsx('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', artifact.triangle.agreement === 'conflict' ? 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300' : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300')}>
                  {artifact.triangle.agreement === 'conflict' ? <AlertTriangle className="size-3.5" /> : <Check className="size-3.5" />}
                  {artifact.triangle.agreement === 'conflict' ? 'Sources disagree' : 'Sources agree'}
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <Side title="The work" side={artifact.triangle.work} />
                <Side title="The feedback" side={artifact.triangle.feedback} />
                <Side title="The voice" side={artifact.triangle.voice} />
              </div>
              <p className="mt-3 text-sm text-slate-700 dark:text-slate-300">{artifact.triangle.note}</p>
            </section>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <AgentCard agent="Cherry" title="The records">
              {queries.length ? (
                <ul className="space-y-2">
                  {queries.map((query, i) => (
                    <li key={query.citation_id}>
                      <button
                        onClick={() => setOpenSource(openSource === query.citation_id ? null : query.citation_id)}
                        className="flex w-full items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-left text-sm hover:bg-slate-100 dark:bg-slate-800/50 dark:hover:bg-slate-800"
                      >
                        <span className="flex items-center gap-2">
                          <Table2 className="size-4" style={{ color: agentColor('Cherry') }} /> Query {i + 1}
                        </span>
                        <span className="text-xs text-slate-500">
                          {query.rows.length} row{query.rows.length === 1 ? '' : 's'} · view
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">No database queries were needed.</p>
              )}
            </AgentCard>

            <AgentCard agent="Vanilla" title="The team's voice" muted={!artifact.voice && !made?.survey_sources}>
              {artifact.voice ? (
                <>
                  <div className="text-sm">
                    {artifact.voice.topic} · {artifact.voice.responses} anonymous responses
                  </div>
                  <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                    <div className="bg-emerald-500" style={{ width: `${artifact.voice.positive}%` }} />
                    <div className="bg-slate-300 dark:bg-slate-600" style={{ width: `${100 - artifact.voice.positive - artifact.voice.negative}%` }} />
                    <div className="bg-rose-500" style={{ width: `${artifact.voice.negative}%` }} />
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    {artifact.voice.positive}% positive · {artifact.voice.negative}% negative · no individual responses shown
                  </div>
                </>
              ) : made?.survey_sources ? (
                <p className="text-sm text-slate-600 dark:text-slate-300">This answer draws on anonymous survey responses. Their text is never shown.</p>
              ) : (
                <p className="text-sm text-slate-500">Survey voice wasn't needed for this question.</p>
              )}
              <button onClick={onOpenPulse} className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">
                <MessagesSquare className="size-4" /> What the team is saying
              </button>
            </AgentCard>

            {chart && chartSource ? (
              <AgentCard agent="Lime" title={chart.title} className="md:col-span-2">
                <EvidenceChart spec={chart} evidence={chartSource} height={260} />
              </AgentCard>
            ) : (
              <AgentCard agent="Lime" title="No chart" muted>
                <p className="text-sm text-slate-500">{artifact.visualization?.reason || 'A chart would not add anything here.'}</p>
              </AgentCard>
            )}

            <AgentCard agent="ZeroSugar" title="The fact-check" className={chart && chartSource ? 'md:col-span-2' : undefined}>
              <ul className="grid gap-1.5 text-sm sm:grid-cols-2">
                <li className="flex items-start gap-2">
                  {verified ? <ShieldCheck className="mt-0.5 size-4 shrink-0 text-emerald-500" /> : <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" />}
                  {verified ? 'Verified before you saw it' : 'Not fully verified — read with care'}
                </li>
                {made && made.findings_checked > 0 && (
                  <li className="flex items-start gap-2">
                    <Check className="mt-0.5 size-4 shrink-0 text-emerald-500" /> {made.findings_checked} claim{made.findings_checked === 1 ? '' : 's'} checked against the data
                  </li>
                )}
                {queries.length > 0 && meta.mode === 'offline' && (
                  <li className="flex items-start gap-2">
                    <Check className="mt-0.5 size-4 shrink-0 text-emerald-500" /> Every query re-run; rows match
                  </li>
                )}
                <li className="flex items-start gap-2">
                  <Check className="mt-0.5 size-4 shrink-0 text-emerald-500" /> Only {managerId}'s team and chosen dates
                </li>
                <li className="flex items-start gap-2">
                  <Check className="mt-0.5 size-4 shrink-0 text-emerald-500" /> No individual survey responses shown
                </li>
                {artifact.triangle?.agreement === 'conflict' && (
                  <li className="flex items-start gap-2 text-amber-700 dark:text-amber-300">
                    <AlertTriangle className="mt-0.5 size-4 shrink-0" /> Flagged: records and survey disagree
                  </li>
                )}
              </ul>
            </AgentCard>
          </div>

          {artifact.examples && artifact.examples.length > 0 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="text-sm font-semibold">Worth reviewing</div>
              <p className="mb-3 text-xs text-slate-500">Cross-team work that drew praise from the team it helped but has no recognition record. A starting point for a conversation, not a rating.</p>
              <ul className="space-y-2">
                {artifact.examples.map((example) => (
                  <li key={example.contribution_id} className="flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium">
                        {example.name} <span className="font-normal text-slate-500">helped {example.team_helped}</span>
                      </div>
                      <div className="text-xs text-slate-500">
                        {example.outcome} · {example.date} · {example.praise_reached_you ? 'their praise was sent to you' : 'their praise did not reach you'}
                      </div>
                    </div>
                    <button onClick={() => setDraft(example)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:hover:border-indigo-500">
                      <PenLine className="size-3.5" /> Draft note
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {(artifact.next_steps?.length > 0 || artifact.watch?.length) && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              {artifact.next_steps?.length > 0 && (
                <>
                  <div className="text-sm font-semibold">What to do first</div>
                  <ol className="mt-2 space-y-1.5 text-sm">
                    {artifact.next_steps.map((step, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="font-semibold text-indigo-500">{i + 1}.</span> {step}
                      </li>
                    ))}
                  </ol>
                </>
              )}
              {artifact.watch && artifact.watch.length > 0 && (
                <div className="mt-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-semibold">How you'll know it helped</div>
                    <button
                      disabled={tracked}
                      onClick={() => onTrack(artifact.watch!)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:bg-emerald-600"
                    >
                      {tracked ? <Check className="size-3.5" /> : <BellPlus className="size-3.5" />} {tracked ? 'Tracking' : 'Track next quarter'}
                    </button>
                  </div>
                  <table className="mt-2 w-full text-left text-sm">
                    <thead className="text-xs text-slate-500">
                      <tr>
                        <th className="py-1 font-medium">Measure</th>
                        <th className="py-1 font-medium">Now</th>
                        <th className="py-1 font-medium">Aim</th>
                      </tr>
                    </thead>
                    <tbody>
                      {artifact.watch.map((item) => (
                        <tr key={item.metric} className="border-t border-slate-100 dark:border-slate-800">
                          <td className="py-1.5">{item.metric}</td>
                          <td className="py-1.5 font-medium tabular-nums">{item.baseline}</td>
                          <td className="py-1.5 text-slate-500">{item.goal}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}

          {artifact.limitations?.length > 0 && (
            <div>
              <button onClick={() => setNotesOpen(!notesOpen)} className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
                Before you act: limitations <ChevronDown className={clsx('size-3.5 transition', notesOpen && 'rotate-180')} />
              </button>
              {notesOpen && (
                <ul className="slide-in mt-2 space-y-1 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-800/50 dark:text-slate-300">
                  {artifact.limitations.map((note, i) => (
                    <li key={i}>• {note}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
      {draft && <DraftNoteDialog example={draft} onClose={() => setDraft(null)} />}
    </div>
  )
}
