import clsx from 'clsx'
import { AlertTriangle, Check } from 'lucide-react'
import { AGENTS } from '../../lib/agents'
import type { AgentState } from '../../lib/events'
import type { AgentName } from '../../lib/agents'

/** Five agent nodes that light up as the execution log streams in. */
export default function Pipeline({ states }: { states: Record<AgentName, AgentState> }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      {AGENTS.map((agent) => {
        const state = states[agent.name]
        return (
          <div
            key={agent.name}
            className={clsx(
              'relative rounded-xl border p-3 transition-all duration-300',
              state.status === 'idle' && 'border-slate-200 opacity-60 dark:border-slate-800',
              state.status === 'active' && 'border-transparent shadow-lg',
              state.status === 'done' && 'border-slate-200 dark:border-slate-700',
              state.status === 'waiting' && 'border-dashed border-slate-300 dark:border-slate-600',
              state.status === 'failed' && 'border-rose-300 bg-rose-50/50 dark:border-rose-500/40 dark:bg-rose-500/5',
            )}
            style={state.status === 'active' ? { boxShadow: `0 0 0 2px ${agent.color}, 0 10px 25px -10px ${agent.color}` } : undefined}
          >
            <div className="flex items-center justify-between">
              <span
                className={clsx('grid size-8 place-items-center rounded-lg text-white', state.status === 'active' && 'pulse-ring')}
                style={{ background: agent.color, color: 'white' }}
              >
                <agent.icon className="size-4" />
              </span>
              {state.status === 'done' && <Check className="size-4 text-emerald-500" />}
              {state.status === 'failed' && <AlertTriangle className="size-4 text-rose-500" />}
              {state.status === 'waiting' && <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Waiting</span>}
              {state.status === 'active' && <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: agent.color }}>Working</span>}
            </div>
            <div className="mt-2 text-sm font-semibold">{agent.name}</div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">{agent.role}</div>
            <div className="mt-2 flex gap-3 text-[11px] text-slate-500 dark:text-slate-400">
              <span>{state.calls} calls</span>
              <span>{state.tools} tools</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
