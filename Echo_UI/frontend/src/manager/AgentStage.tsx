import clsx from 'clsx'
import { AlertTriangle, Check } from 'lucide-react'
import { AGENTS, type AgentName } from '../lib/agents'
import type { AgentState } from '../lib/events'

/** Newsroom roles: how the five agents are introduced to managers. */
export const NEWSROOM: Record<AgentName, { title: string; line: string }> = {
  Original: { title: 'Editor', line: 'Plans the investigation and writes your brief' },
  Cherry: { title: 'Data reporter', line: 'Finds the work and feedback in the records' },
  Vanilla: { title: 'Listener', line: 'Hears what the team says, as themes only' },
  Lime: { title: 'Graphics desk', line: 'Shows the evidence as a chart' },
  ZeroSugar: { title: 'Fact-checker', line: 'Re-checks every claim and flags conflicts' },
}

// Original sits in the middle; the four specialists around it (percent of the stage box).
const POSITION: Record<AgentName, { x: number; y: number }> = {
  Original: { x: 50, y: 50 },
  Cherry: { x: 17, y: 25 },
  Vanilla: { x: 83, y: 25 },
  Lime: { x: 17, y: 75 },
  ZeroSugar: { x: 83, y: 75 },
}

export default function AgentStage({
  states,
  activity,
  busy,
  headline,
}: {
  states: Record<AgentName, AgentState>
  activity: Partial<Record<AgentName, string>>
  busy: boolean
  headline?: string
}) {
  const color = (name: AgentName) => AGENTS.find((a) => a.name === name)!.color

  return (
    <div className="relative h-[340px] overflow-hidden rounded-3xl border border-slate-200 bg-white sm:h-[380px] dark:border-slate-800 dark:bg-slate-900">
      {/* soft dotted backdrop */}
      <div
        className="pointer-events-none absolute inset-0 opacity-60 dark:opacity-30"
        style={{ backgroundImage: 'radial-gradient(circle, rgb(148 163 184 / 0.35) 1px, transparent 1px)', backgroundSize: '22px 22px' }}
      />
      <div className="pointer-events-none absolute left-1/2 top-1/2 size-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500/10 blur-3xl" />

      {/* links from the editor to each specialist; a working link glows and flows in that agent's colour */}
      <svg className="absolute inset-0 size-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
        {AGENTS.filter((a) => a.name !== 'Original').map((agent) => {
          const p = POSITION[agent.name]
          const active = states[agent.name].status === 'active'
          const done = states[agent.name].status === 'done'
          return (
            <g key={agent.name}>
              <line x1={50} y1={50} x2={p.x} y2={p.y} stroke="rgb(148 163 184 / 0.35)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
              {(active || done) && (
                <line
                  x1={50}
                  y1={50}
                  x2={p.x}
                  y2={p.y}
                  stroke={agent.color}
                  strokeWidth={active ? 3 : 2}
                  strokeOpacity={active ? 1 : 0.45}
                  strokeDasharray={active ? '6 8' : undefined}
                  vectorEffect="non-scaling-stroke"
                  className={active ? 'flow-dash' : undefined}
                />
              )}
            </g>
          )
        })}
      </svg>

      {AGENTS.map((agent) => {
        const state = states[agent.name]
        const p = POSITION[agent.name]
        const isEditor = agent.name === 'Original'
        const active = state.status === 'active'
        const dim = busy && state.status === 'idle'
        const status = busy
          ? activity[agent.name] ?? (state.status === 'waiting' ? 'Waiting on the desk' : state.status === 'done' ? 'Done' : 'Standing by')
          : NEWSROOM[agent.name].line
        return (
          <div
            key={agent.name}
            className={clsx('absolute flex w-36 -translate-x-1/2 -translate-y-1/2 flex-col items-center text-center transition-all duration-500 sm:w-44', dim && 'opacity-40')}
            style={{ left: `${p.x}%`, top: `${p.y}%` }}
          >
            <div
              className={clsx(
                'relative grid place-items-center rounded-full text-white shadow-lg transition-all duration-500',
                isEditor ? 'size-20 sm:size-24' : 'size-14 sm:size-16',
                active && 'scale-110',
              )}
              style={{
                background: `radial-gradient(circle at 30% 25%, color-mix(in srgb, ${color(agent.name)} 70%, white), ${color(agent.name)})`,
                boxShadow: active ? `0 0 0 6px color-mix(in srgb, ${color(agent.name)} 25%, transparent), 0 12px 40px -6px ${color(agent.name)}` : undefined,
              }}
            >
              {active && <span className="absolute inset-0 animate-ping rounded-full opacity-30" style={{ background: color(agent.name) }} />}
              <agent.icon className={isEditor ? 'size-8 sm:size-10' : 'size-6 sm:size-7'} />
              {state.status === 'done' && (
                <span className="absolute -right-0.5 -top-0.5 grid size-5 place-items-center rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900">
                  <Check className="size-3" strokeWidth={3} />
                </span>
              )}
              {state.status === 'failed' && (
                <span className="absolute -right-0.5 -top-0.5 grid size-5 place-items-center rounded-full bg-rose-500 ring-2 ring-white dark:ring-slate-900">
                  <AlertTriangle className="size-3" strokeWidth={3} />
                </span>
              )}
            </div>
            <div className="mt-2 text-sm font-semibold leading-tight">{agent.name}</div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{NEWSROOM[agent.name].title}</div>
            <div
              className={clsx('mt-1 hidden min-h-8 text-xs leading-snug sm:block', active ? 'font-medium' : 'text-slate-500 dark:text-slate-400')}
              style={active ? { color: color(agent.name) } : undefined}
            >
              {status}
            </div>
          </div>
        )
      })}

      {headline && (
        <div className="absolute inset-x-0 bottom-3 text-center text-xs font-medium text-slate-500 dark:text-slate-400">{headline}</div>
      )}
    </div>
  )
}
