import clsx from 'clsx'
import { ArrowRight, CalendarRange, FlaskConical, Radio, Sparkles, UserRound } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { PageTitle } from '../components/Layout'
import { Badge, Button, Card, CardHeader, ErrorNote, inputClass } from '../components/ui'
import { AGENTS } from '../lib/agents'
import { api } from '../lib/api'
import { fmtDate, STATE_TONE } from '../lib/format'
import { useAsync } from '../lib/useAsync'

const SPLIT = '__split__'

export default function Ask() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const meta = useAsync(api.meta)
  const managers = useAsync(api.managers)
  const runs = useAsync(api.runs)

  const [manager, setManager] = useState(params.get('manager') ?? 'M14')
  const [start, setStart] = useState('2024-10-01')
  const [end, setEnd] = useState('2026-09-30')
  const [mode, setMode] = useState<'demo' | 'live'>(params.get('q') ? 'live' : 'demo')
  const [profile, setProfile] = useState('')
  const [question, setQuestion] = useState(params.get('q') ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const liveOptions = useMemo(() => {
    const options: { value: string; label: string; ready: boolean }[] = []
    if (meta.data?.local_split) options.push({ value: SPLIT, label: 'Per-agent Gemini split (connections.local.json)', ready: true })
    for (const p of meta.data?.profiles ?? [])
      options.push({ value: p.name, label: `${p.name}${p.model ? ` · ${p.model}` : ''}`, ready: p.key_configured })
    return options
  }, [meta.data])

  useEffect(() => {
    if (!profile && liveOptions.length) setProfile((liveOptions.find((o) => o.ready) ?? liveOptions[0]).value)
  }, [liveOptions, profile])

  const selectedManager = managers.data?.find((m) => m.Manager_ID === manager)

  async function submit() {
    setSubmitting(true)
    setError(null)
    try {
      const run = await api.startRun({
        manager_id: manager,
        start_date: start,
        end_date: end,
        question,
        mode,
        profile: profile === SPLIT ? null : profile,
        use_local_split: profile === SPLIT,
      })
      navigate(`/console/runs/${run.id}`)
    } catch (e) {
      setError(e)
      setSubmitting(false)
    }
  }

  const canSubmit = mode === 'demo' || question.trim().length > 3

  return (
    <>
      <PageTitle title="Ask Echo" subtitle="Five agents plan, query, retrieve, chart and review — every claim is tied to scoped evidence." />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Scope" subtitle="Echo only sees data for this manager's pilot team and date window." icon={UserRound} />
            <div className="grid gap-4 p-5 sm:grid-cols-3">
              <label className="sm:col-span-1">
                <span className="mb-1.5 block text-xs font-medium text-slate-500">Manager</span>
                <select className={inputClass} value={manager} onChange={(e) => setManager(e.target.value)}>
                  {(managers.data ?? []).map((m) => (
                    <option key={m.Manager_ID} value={m.Manager_ID}>
                      {m.Manager_ID} · {m.Manager_Name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="mb-1.5 flex items-center gap-1 text-xs font-medium text-slate-500">
                  <CalendarRange className="size-3.5" /> From
                </span>
                <input type="date" className={inputClass} value={start} min={meta.data?.scope_min} max={end} onChange={(e) => setStart(e.target.value)} />
              </label>
              <label>
                <span className="mb-1.5 block text-xs font-medium text-slate-500">To</span>
                <input type="date" className={inputClass} value={end} min={start} max={meta.data?.scope_max} onChange={(e) => setEnd(e.target.value)} />
              </label>
              {selectedManager && (
                <p className="text-xs text-slate-500 sm:col-span-3">
                  {selectedManager.Primary_Department} · {selectedManager.Primary_Team} · {selectedManager.Pilot_Assigned_Employees} pilot employees.
                  The manager selection is a demo scope, not authentication.
                </p>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader title="Question" icon={Sparkles} />
            <div className="space-y-4 p-5">
              <div className="grid gap-2 sm:grid-cols-2">
                {(
                  [
                    { id: 'demo', icon: FlaskConical, title: 'Offline demo', text: 'Scripted fixture with real local tools. 0 API calls, no quota.' },
                    { id: 'live', icon: Radio, title: 'Live models', text: 'Real model calls through your configured provider.' },
                  ] as const
                ).map((option) => (
                  <button
                    key={option.id}
                    onClick={() => setMode(option.id)}
                    className={clsx(
                      'flex items-start gap-3 rounded-xl border p-3 text-left transition',
                      mode === option.id
                        ? 'border-indigo-400 bg-indigo-50/60 ring-4 ring-indigo-500/10 dark:border-indigo-500 dark:bg-indigo-500/10'
                        : 'border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600',
                    )}
                  >
                    <option.icon className={clsx('mt-0.5 size-4', mode === option.id ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-400')} />
                    <span>
                      <span className="block text-sm font-medium">{option.title}</span>
                      <span className="block text-xs text-slate-500 dark:text-slate-400">{option.text}</span>
                    </span>
                  </button>
                ))}
              </div>

              {mode === 'live' && (
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-500">Model connection</span>
                  <select className={inputClass} value={profile} onChange={(e) => setProfile(e.target.value)}>
                    {liveOptions.map((o) => (
                      <option key={o.value} value={o.value} disabled={!o.ready}>
                        {o.label}
                        {o.ready ? '' : ' (no key configured)'}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <textarea
                className={clsx(inputClass, 'min-h-28 resize-y leading-relaxed')}
                placeholder={mode === 'demo' ? 'The offline demo runs a fixed recognition review; your question is not sent anywhere.' : 'Ask about recognition, workload, contributions, survey comments…'}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && canSubmit) submit()
                }}
              />
              <div className="flex flex-wrap gap-2">
                {meta.data?.suggested_questions.map((q) => (
                  <button
                    key={q}
                    onClick={() => setQuestion(q)}
                    className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:text-indigo-300"
                  >
                    {q}
                  </button>
                ))}
              </div>
              {error ? <ErrorNote error={error} /> : null}
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
                <span className="text-xs text-slate-500">
                  {mode === 'live'
                    ? 'A full question typically needs 15–30 model calls across the agents.'
                    : 'Demo answers are scripted to exercise the pipeline, not to evaluate a model.'}
                </span>
                <Button variant="primary" icon={ArrowRight} loading={submitting} disabled={!canSubmit} onClick={submit}>
                  {mode === 'demo' ? 'Run demo' : 'Ask Echo'}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="How a question flows" icon={Sparkles} />
            <ol className="space-y-3 p-5">
              {AGENTS.map((agent, index) => (
                <li key={agent.name} className="flex gap-3">
                  <span className="grid size-8 shrink-0 place-items-center rounded-lg text-white" style={{ background: agent.color }}>
                    <agent.icon className="size-4" />
                  </span>
                  <div className="text-sm">
                    <div className="font-medium">
                      {index + 1}. {agent.name} <span className="font-normal text-slate-500">· {agent.role}</span>
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">{agent.detail}</div>
                  </div>
                </li>
              ))}
            </ol>
          </Card>

          <Card>
            <CardHeader title="Recent runs" icon={Sparkles} action={<Link to="/console/runs" className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400">All runs</Link>} />
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {(runs.data ?? []).slice(0, 5).map((run) => (
                <li key={run.id}>
                  <Link to={`/console/runs/${run.id}`} className="block px-5 py-3 transition hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <div className="truncate text-sm font-medium">{run.question}</div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                      <Badge tone={STATE_TONE[run.state] ?? 'slate'}>{run.state}</Badge>
                      {run.manager_id} · {run.mode} · {fmtDate(run.created_at)}
                    </div>
                  </Link>
                </li>
              ))}
              {runs.data?.length === 0 && <li className="px-5 py-4 text-sm text-slate-500">No runs yet.</li>}
            </ul>
          </Card>
        </div>
      </div>
    </>
  )
}
