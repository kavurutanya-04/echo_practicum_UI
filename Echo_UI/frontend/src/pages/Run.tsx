import { Activity, AlertTriangle, ArrowLeft, Braces, Download, Printer, RotateCcw, Square, Workflow } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Answer, { CitedText } from '../components/run/Answer'
import Charts from '../components/run/Charts'
import EvidenceList from '../components/run/Evidence'
import Pipeline from '../components/run/Pipeline'
import Review from '../components/run/Review'
import Sentiment from '../components/run/Sentiment'
import Timeline from '../components/run/Timeline'
import { Badge, Button, Card, CardHeader, Empty, ErrorNote, Spinner, Tabs } from '../components/ui'
import { agentByName } from '../lib/agents'
import { api } from '../lib/api'
import { agentStates, useRunEvents } from '../lib/events'
import { duration, fmtDate, STATE_TONE } from '../lib/format'
import { useAsync } from '../lib/useAsync'

type Tab = 'answer' | 'evidence' | 'charts' | 'review' | 'sentiment' | 'specialists' | 'raw'

function failureHint(console: string) {
  if (/HTTP 429/.test(console)) return { text: 'The model provider returned a quota error (HTTP 429). Free-tier daily limits reset at midnight Pacific.', link: '/console/connections' }
  if (/HTTP 503/.test(console)) return { text: 'The model was overloaded (HTTP 503). Try again later or switch models.', link: '/console/connections' }
  if (/timeout|did not respond/i.test(console)) return { text: 'A model call timed out. Slower preview models may need a longer timeout.', link: '/console/connections' }
  return null
}

export default function Run() {
  const { id } = useParams()
  const detail = useAsync(() => api.run(id!), [id])
  const [replayKey, setReplayKey] = useState(0)
  const [pace, setPace] = useState<number | null>(null)
  const [tab, setTab] = useState<Tab>('answer')
  const [cancelling, setCancelling] = useState(false)

  const meta = detail.data?.meta
  // Demo runs finish instantly, so they replay at a readable pace; live runs stream in real time.
  const effectivePace = pace ?? (meta?.mode === 'demo' ? 70 : 0)
  const stream = useRunEvents(meta ? id : undefined, effectivePace, replayKey)
  const states = useMemo(() => agentStates(stream.events), [stream.events])

  useEffect(() => {
    if (stream.done) detail.reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream.done])

  if (detail.loading && !detail.data) return <Spinner />
  if (detail.error) return <ErrorNote error={detail.error} />
  if (!meta) return null

  const artifact = detail.data!.artifact
  const running = meta.state === 'running'
  const streaming = !stream.done
  const hint = meta.state === 'failed' ? failureHint(detail.data!.console) : null
  const evidenceCount = (artifact?.evidence ?? []).length
  const chartCount = artifact?.visualization?.charts?.length ?? 0
  const hasSentiment = artifact && Object.keys(artifact.sentiment ?? {}).length > 0

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'answer', label: 'Answer' },
    { id: 'evidence', label: 'Evidence', count: evidenceCount },
    { id: 'charts', label: 'Charts', count: chartCount },
    { id: 'review', label: 'Review' },
    ...(hasSentiment ? [{ id: 'sentiment' as Tab, label: 'Sentiment' }] : []),
    { id: 'specialists', label: 'Specialists', count: artifact?.delegations?.length ?? 0 },
    { id: 'raw', label: 'Raw' },
  ]

  function downloadArtifact() {
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([JSON.stringify(artifact, null, 2)], { type: 'application/json' }))
    link.download = `echo_${meta!.id}.json`
    link.click()
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/console/runs" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 print:hidden">
          <ArrowLeft className="size-4" /> All runs
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{meta.question}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
              <Badge tone={STATE_TONE[meta.state] ?? 'slate'}>{meta.state}</Badge>
              {meta.verification && <Badge tone={STATE_TONE[meta.verification] ?? 'slate'}>review: {meta.verification}</Badge>}
              <Badge tone={meta.mode === 'demo' ? 'slate' : 'blue'}>{meta.mode === 'demo' ? 'offline demo' : meta.profile}</Badge>
              <span>
                {meta.manager_id} · {meta.start_date} → {meta.end_date}
              </span>
              <span>· {fmtDate(meta.created_at)}</span>
              {meta.finished_at && <span>· {duration(meta.created_at, meta.finished_at)}</span>}
              {meta.api_calls !== undefined && <span>· {meta.api_calls} API calls</span>}
            </div>
            {meta.mode === 'demo' && meta.typed_question && (
              <p className="mt-2 text-xs text-slate-500">You typed “{meta.typed_question}”, but offline demos always run Echo's fixed scripted recognition review.</p>
            )}
          </div>
          <div className="flex gap-2 print:hidden">
            {running ? (
              <Button
                variant="danger"
                icon={Square}
                loading={cancelling}
                onClick={async () => {
                  setCancelling(true)
                  await api.cancelRun(meta.id).catch(() => undefined)
                }}
              >
                Cancel
              </Button>
            ) : (
              <>
                <Button
                  icon={RotateCcw}
                  onClick={() => {
                    setPace(meta.mode === 'demo' ? 70 : 40)
                    setReplayKey((k) => k + 1)
                  }}
                >
                  Replay
                </Button>
                {artifact && <Button icon={Download} onClick={downloadArtifact}>JSON</Button>}
                {artifact && <Button icon={Printer} onClick={() => window.print()}>Print</Button>}
              </>
            )}
          </div>
        </div>
      </div>

      {hint && (
        <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <div>
            {hint.text}{' '}
            <Link to={hint.link} className="font-medium underline">
              Check usage
            </Link>
          </div>
        </div>
      )}

      <Card className="print:hidden">
        <CardHeader
          title="Agent pipeline"
          subtitle={streaming ? (running ? 'Live — streaming from the execution log' : 'Replaying the execution log') : `${stream.events.length} logged events`}
          icon={Workflow}
          action={streaming && <Activity className="size-4 animate-pulse text-indigo-500" />}
        />
        <div className="p-5">
          <Pipeline states={states} />
        </div>
        <div className="border-t border-slate-100 dark:border-slate-800">
          <Timeline events={stream.events} live={streaming} />
        </div>
      </Card>

      <Card>
        <div className="border-b border-slate-100 p-3 print:hidden dark:border-slate-800">
          <Tabs tabs={tabs} value={tab} onChange={setTab} />
        </div>
        <div className="p-5 sm:p-6">
          {!artifact && tab !== 'raw' ? (
            running ? <Spinner label="Echo is working — results appear when the run finishes." /> : <Empty icon={Braces} title="No result artifact">This run ended before Echo wrote a result. See the Raw tab.</Empty>
          ) : !artifact ? (
            <pre className="max-h-80 overflow-auto rounded-xl bg-slate-950 p-4 font-mono text-xs leading-relaxed text-slate-200">{detail.data!.console}</pre>
          ) : tab === 'answer' ? (
            <Answer artifact={artifact} />
          ) : tab === 'evidence' ? (
            evidenceCount ? <EvidenceList evidence={artifact.evidence} /> : <Empty icon={Braces} title="No evidence released" />
          ) : tab === 'charts' ? (
            <Charts artifact={artifact} runId={meta.id} />
          ) : tab === 'review' ? (
            <Review artifact={artifact} />
          ) : tab === 'sentiment' ? (
            <Sentiment reports={artifact.sentiment} />
          ) : tab === 'specialists' ? (
            <div className="space-y-4">
              {(artifact.delegations ?? []).map((d, i) => {
                const agent = agentByName(d.agent)
                return (
                  <div key={i} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="rounded-md px-2 py-0.5 text-xs font-semibold text-white" style={{ background: agent?.color }}>
                        {d.agent}
                      </span>
                      <span className="text-xs text-slate-500">asked by Original</span>
                    </div>
                    <p className="text-sm font-medium">{d.question}</p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                      <CitedText text={d.answer} onCite={() => setTab('evidence')} known={new Set((d.evidence ?? []).map((e) => e.citation_id))} />
                    </p>
                  </div>
                )
              })}
              {!artifact.delegations?.length && <Empty icon={Workflow} title="No specialist delegations" />}
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <h4 className="mb-2 text-sm font-semibold">Terminal output</h4>
                <pre className="max-h-80 overflow-auto rounded-xl bg-slate-950 p-4 font-mono text-xs leading-relaxed text-slate-200">{detail.data!.console}</pre>
              </div>
              <div>
                <h4 className="mb-2 text-sm font-semibold">Artifact JSON</h4>
                <pre className="max-h-[480px] overflow-auto rounded-xl bg-slate-100 p-4 font-mono text-xs dark:bg-slate-800/60">{JSON.stringify(artifact, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
