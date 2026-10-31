import clsx from 'clsx'
import { AlertTriangle, Check, Maximize2, Minimize2 } from 'lucide-react'
import type { CSSProperties } from 'react'
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

// The middle seat and the four around it (percent of the stage box).
const CENTER = { x: 50, y: 38 }
const CORNERS = [
  { x: 17, y: 18 },
  { x: 83, y: 18 },
  { x: 17, y: 64 },
  { x: 83, y: 64 },
]
// At rest the editor sits in the middle; each specialist keeps its own corner.
const HOME: Record<AgentName, number> = { Original: -1, Cherry: 0, Vanilla: 1, Lime: 2, ZeroSugar: 3 }

/** Which agent is working right now: a specialist if one is active, otherwise the editor. */
function runningAgent(states: Record<AgentName, AgentState>): AgentName | null {
  const active = AGENTS.filter((a) => states[a.name].status === 'active').map((a) => a.name)
  return active.find((name) => name !== 'Original') ?? active[0] ?? null
}

export default function AgentStage({
  states,
  activity,
  busy,
  headline,
  onMinimize,
}: {
  states: Record<AgentName, AgentState>
  activity: Partial<Record<AgentName, string>>
  busy: boolean
  headline?: string
  onMinimize?: () => void
}) {
  const running = busy ? runningAgent(states) : null
  const center: AgentName = running ?? 'Original'
  // The running agent swaps seats with the editor, so everyone else stays where they were.
  const seat = (name: AgentName) => {
    if (name === center) return CENTER
    if (name === 'Original') return CORNERS[HOME[center]]
    return CORNERS[HOME[name]]
  }
  const color = (name: AgentName) => AGENTS.find((a) => a.name === name)!.color

  return (
    <div className="relative h-[360px] overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-br from-white via-white to-indigo-50/70 sm:h-[390px] dark:border-slate-800 dark:from-slate-900 dark:via-slate-900 dark:to-slate-900">
      {/* one soft wash behind the middle seat, in the running agent's colour */}
      <div
        className="pointer-events-none absolute left-1/2 top-[38%] size-[360px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-60 blur-3xl transition-colors duration-700 dark:opacity-25"
        style={{ background: `color-mix(in srgb, ${color(center)} 22%, transparent)` }}
      />

      {/* links from the middle seat to each corner; a finished agent's link stays tinted */}
      <svg className="absolute inset-0 size-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
        {CORNERS.map((corner, i) => {
          const occupant = AGENTS.find((a) => a.name !== center && seat(a.name) === corner)!
          const done = states[occupant.name].status === 'done'
          return (
            <g key={i}>
              <line x1={CENTER.x} y1={CENTER.y} x2={corner.x} y2={corner.y} stroke="currentColor" className="text-slate-200 dark:text-slate-700" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
              {/* while a specialist works in the middle, its link back to the editor flows */}
              {(done || (running && center !== 'Original' && i === HOME[center])) && (
                <line
                  x1={CENTER.x}
                  y1={CENTER.y}
                  x2={corner.x}
                  y2={corner.y}
                  stroke={done ? occupant.color : color(center)}
                  strokeWidth={done ? 2 : 2.5}
                  strokeOpacity={done ? 0.55 : 0.9}
                  strokeDasharray={done ? undefined : '6 8'}
                  vectorEffect="non-scaling-stroke"
                  className={done ? undefined : 'flow-dash'}
                />
              )}
            </g>
          )
        })}
      </svg>

      {AGENTS.map((agent) => {
        const state = states[agent.name]
        const p = seat(agent.name)
        const inCenter = agent.name === center
        const active = state.status === 'active' && inCenter && busy
        const dim = busy && !inCenter && state.status === 'idle'
        const status = busy
          ? activity[agent.name] ?? (state.status === 'waiting' ? 'Waiting on the desk' : state.status === 'done' ? 'Done' : 'Standing by')
          : NEWSROOM[agent.name].line
        return (
          <div
            key={agent.name}
            className={clsx(
              'absolute flex -translate-x-1/2 flex-col items-center text-center transition-all duration-700 ease-in-out',
              // shift up by half the circle, so the circle (not the whole block) is centred on its seat
              inCenter ? 'z-10 w-48 -translate-y-10 sm:w-60 sm:-translate-y-12' : 'w-32 -translate-y-6 sm:w-44 sm:-translate-y-7',
              dim && 'opacity-45',
            )}
            style={{ left: `${p.x}%`, top: `${p.y}%` }}
          >
            <div
              className={clsx(
                'agent-tint relative grid place-items-center rounded-full ring-[6px] ring-white transition-all duration-700 dark:ring-slate-900',
                inCenter ? 'size-20 sm:size-24' : 'size-12 sm:size-14',
              )}
              style={{ '--agent': agent.color, boxShadow: active ? `0 0 0 10px color-mix(in srgb, ${agent.color} 18%, transparent)` : undefined } as CSSProperties}
            >
              {active && <span className="absolute inset-0 animate-ping rounded-full opacity-20" style={{ background: agent.color }} />}
              <agent.icon className={clsx('transition-all duration-700', inCenter ? 'size-8 sm:size-10' : 'size-5 sm:size-6')} />
              {state.status === 'done' && (
                <span className="absolute -right-0.5 -top-0.5 grid size-5 place-items-center rounded-full bg-indigo-500 text-white ring-2 ring-white dark:ring-slate-900">
                  <Check className="size-3" strokeWidth={3} />
                </span>
              )}
              {state.status === 'failed' && (
                <span className="absolute -right-0.5 -top-0.5 grid size-5 place-items-center rounded-full bg-rose-400 text-white ring-2 ring-white dark:ring-slate-900">
                  <AlertTriangle className="size-3" strokeWidth={3} />
                </span>
              )}
            </div>
            <div className="mt-1.5 flex flex-col items-center rounded-xl bg-white/85 px-2 pb-0.5 backdrop-blur-[2px] dark:bg-slate-900/85">
            {active && <div className="mt-1 rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-medium text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-200">Working now</div>}
            <div className={clsx('font-semibold leading-tight', active ? 'mt-1 text-base' : 'mt-0.5 text-sm')}>{agent.name}</div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">{NEWSROOM[agent.name].title}</div>
            <div
              className={clsx('mt-1 hidden min-h-8 text-xs leading-snug sm:block', active ? 'font-medium text-slate-700 dark:text-slate-200' : 'text-slate-500 dark:text-slate-400')}
            >
              {status}
            </div>
            </div>
          </div>
        )
      })}

      {onMinimize && (
        <button
          onClick={onMinimize}
          className="absolute right-3 top-3 z-20 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white/90 px-2.5 py-1.5 text-xs font-medium text-slate-600 shadow-sm backdrop-blur transition hover:border-indigo-300 hover:text-indigo-800 dark:border-slate-700 dark:bg-slate-900/90 dark:text-slate-300"
          aria-label="Minimize the newsroom"
        >
          <Minimize2 className="size-3.5" /> Minimize
        </button>
      )}

      {headline && (
        <div className="absolute inset-x-0 bottom-3 text-center text-xs text-slate-500 dark:text-slate-400" aria-live="polite">
          {headline}
        </div>
      )}
    </div>
  )
}

/** The newsroom folded into one line: five small agents, the one working now highlighted. */
export function AgentStageMini({
  states,
  activity,
  busy,
  headline,
  onExpand,
}: {
  states: Record<AgentName, AgentState>
  activity: Partial<Record<AgentName, string>>
  busy: boolean
  headline?: string
  onExpand: () => void
}) {
  const running = busy ? runningAgent(states) : null
  const line = running ? `${running}: ${activity[running] ?? NEWSROOM[running].title}` : headline
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-gradient-to-r from-white to-indigo-50/60 px-3 py-2.5 sm:px-4 dark:border-slate-800 dark:from-slate-900 dark:to-slate-900">
      <div className="flex shrink-0 -space-x-1.5">
        {AGENTS.map((agent) => {
          const state = states[agent.name]
          const on = agent.name === running
          return (
            <div
              key={agent.name}
              title={`${agent.name} · ${NEWSROOM[agent.name].title}`}
              className={clsx(
                'agent-tint relative grid place-items-center rounded-full ring-2 ring-white transition-all duration-500 dark:ring-slate-900',
                on ? 'z-10 size-9' : 'size-7',
                busy && !on && state.status === 'idle' && 'opacity-45',
              )}
              style={{ '--agent': agent.color } as CSSProperties}
            >
              {on && <span className="absolute inset-0 animate-ping rounded-full opacity-25" style={{ background: agent.color }} />}
              <agent.icon className={on ? 'size-4' : 'size-3.5'} />
              {state.status === 'done' && (
                <span className="absolute -bottom-0.5 -right-0.5 grid size-3 place-items-center rounded-full bg-indigo-500 text-white ring-1 ring-white dark:ring-slate-900">
                  <Check className="size-2" strokeWidth={3.5} />
                </span>
              )}
            </div>
          )
        })}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">The newsroom</div>
        <div className="truncate text-xs text-slate-500 dark:text-slate-400" aria-live="polite">{line}</div>
      </div>
      <button
        onClick={onExpand}
        className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:border-indigo-300 hover:text-indigo-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
        aria-label="Expand the newsroom"
      >
        <Maximize2 className="size-3.5" /> Expand
      </button>
    </div>
  )
}
