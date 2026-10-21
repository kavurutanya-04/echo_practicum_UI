import clsx from 'clsx'
import { CheckCircle2, CircleDashed, Gauge, KeyRound, PlugZap, Split } from 'lucide-react'
import { PageTitle } from '../components/Layout'
import { Badge, Card, CardHeader, Empty, ErrorNote, Spinner } from '../components/ui'
import { agentByName } from '../lib/agents'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'
import { useAsync } from '../lib/useAsync'

export default function Connections() {
  const meta = useAsync(api.meta)
  const quota = useAsync(api.quota)

  return (
    <>
      <PageTitle title="Connections" subtitle="Model profiles Echo can use. Keys stay in Agent_Echo/.env and are never sent to the browser." />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          {meta.loading && !meta.data ? (
            <Spinner />
          ) : meta.error ? (
            <ErrorNote error={meta.error} />
          ) : (
            <>
              {meta.data!.local_split && (
                <Card>
                  <CardHeader title="Per-agent model split" subtitle="connections.local.json — each agent uses its own model and daily quota" icon={Split} action={<Badge tone="green">active option</Badge>} />
                  <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
                    {Object.entries(meta.data!.local_split).map(([agent, model]) => (
                      <div key={agent} className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                        <div className="flex items-center gap-2 text-sm font-semibold">
                          <span className="size-2 rounded-full" style={{ background: agentByName(agent)?.color }} /> {agent}
                        </div>
                        <div className="mt-1 break-all font-mono text-xs text-slate-500">{model}</div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
              <Card>
                <CardHeader title="Profiles in connections.json" icon={PlugZap} />
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {meta.data!.profiles.map((profile) => (
                    <li key={profile.name} className="flex items-start gap-4 px-5 py-4">
                      {profile.key_configured ? <CheckCircle2 className="mt-0.5 size-5 text-emerald-500" /> : <CircleDashed className="mt-0.5 size-5 text-slate-300" />}
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-sm font-medium">{profile.name}</span>
                          <Badge>{profile.provider}</Badge>
                          {profile.name === meta.data!.default_profile && <Badge tone="blue">group default</Badge>}
                        </div>
                        <div className="mt-1 font-mono text-xs text-slate-500">{profile.model || 'model not set'}</div>
                        {profile.description && <p className="mt-1 text-xs text-slate-500">{profile.description}</p>}
                      </div>
                      <Badge tone={profile.key_configured ? 'green' : 'slate'}>
                        <KeyRound className="size-3" /> {profile.key_configured ? 'key set' : 'no key'}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </Card>
            </>
          )}
        </div>

        <Card className="h-fit">
          <CardHeader title="Free-tier usage today" subtitle={quota.data ? `Resets ${fmtDate(quota.data.resets_at)} (midnight Pacific)` : undefined} icon={Gauge} />
          {quota.loading && !quota.data ? (
            <Spinner />
          ) : !quota.data?.models.length ? (
            <Empty icon={Gauge} title="No live calls today" />
          ) : (
            <div className="space-y-4 p-5">
              {quota.data.models.map((m) => {
                const share = Math.min(100, (m.calls / quota.data!.limit_per_model) * 100)
                return (
                  <div key={m.model}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-mono text-xs">{m.model}</span>
                      <span className="tabular-nums text-slate-500">
                        {m.calls} / {quota.data!.limit_per_model}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div className={clsx('h-full rounded-full transition-all', share >= 100 ? 'bg-rose-500' : share >= 70 ? 'bg-amber-500' : 'bg-indigo-500')} style={{ width: `${share}%` }} />
                    </div>
                    {m.quota_errors > 0 && <div className="mt-1 text-xs text-rose-600">{m.quota_errors} quota error{m.quota_errors === 1 ? '' : 's'} (HTTP 429)</div>}
                  </div>
                )
              })}
              <p className="text-xs text-slate-500">{quota.data.note} The limit shown is Gemini's free tier ({quota.data.limit_per_model} requests/day per model).</p>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
