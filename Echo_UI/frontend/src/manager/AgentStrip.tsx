import clsx from 'clsx'
import { AlertTriangle, Check } from 'lucide-react'
import { AGENTS, type AgentName } from '../lib/agents'
import type { LogEvent } from '../lib/api'
import type { AgentState } from '../lib/events'

const TOOL_TEXT: Record<string, string> = {
  submit_plan: 'Planning the answer',
  ask_cherry: 'Asking Cherry for numbers',
  ask_vanilla: 'Asking Vanilla for survey themes',
  describe_schema: 'Reading the data layout',
  execute_sql: 'Running a data query',
  search_text: 'Searching survey responses',
  analyze_survey_sentiment: 'Measuring survey sentiment',
  submit_visuals: 'Choosing a chart',
  submit_review: 'Checking the answer',
}

/** Plain-language "what is this agent doing" line for each agent. */
export function agentActivity(events: LogEvent[]): Partial<Record<AgentName, string>> {
  const activity: Partial<Record<AgentName, string>> = {}
  for (const event of events) {
    const agent = AGENTS.find((a) => a.name.toLowerCase() === (event.agent ?? '').toLowerCase())?.name
    if (!agent) continue
    if (event.event === 'tool_started' && event.tool) activity[agent] = TOOL_TEXT[event.tool] ?? 'Working'
    else if (event.event === 'model_started') activity[agent] = activity[agent] ?? 'Thinking'
    else if (event.event === 'model_finished' && event.tools?.[0]) activity[agent] = TOOL_TEXT[event.tools[0]] ?? 'Thinking'
    else if (event.event === 'sentiment_batch_started') activity[agent] = `Reading responses (batch ${event.batch}/${event.batches})`
    else if (event.event === 'visual_plan_validated') activity[agent] = 'Chart ready'
    else if (event.event === 'verification_finished') activity[agent] = event.decision === 'accept' ? 'Answer verified' : 'Asked for a revision'
    else if (event.event === 'agent_finished') activity[agent] = 'Done'
    else if (event.event === 'model_failed' || event.event === 'agent_failed') activity[agent] = 'Hit a problem'
  }
  return activity
}

/** The five agents across the top of the chat; they light up while they work. */
export default function AgentStrip({ states, activity, busy }: { states: Record<AgentName, AgentState>; activity: Partial<Record<AgentName, string>>; busy: boolean }) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {AGENTS.map((agent) => {
        const state = states[agent.name]
        const active = state.status === 'active'
        const idle = !busy && state.status === 'idle'
        return (
          <div
            key={agent.name}
            className={clsx(
              'relative flex min-w-0 flex-col items-center rounded-2xl border px-2 py-2.5 text-center transition-all duration-300 sm:flex-row sm:gap-2.5 sm:text-left',
              active ? 'border-transparent bg-white shadow-lg dark:bg-slate-900' : 'border-slate-200 bg-white/60 dark:border-slate-800 dark:bg-slate-900/40',
              busy && state.status === 'idle' && 'opacity-45',
              state.status === 'failed' && 'border-rose-300 dark:border-rose-500/40',
            )}
            style={active ? { boxShadow: `0 0 0 2px ${agent.color}, 0 8px 24px -8px ${agent.color}` } : undefined}
          >
            <span
              className={clsx('relative grid size-9 shrink-0 place-items-center rounded-xl text-white transition', active && 'pulse-ring', idle && 'opacity-90')}
              style={{ background: agent.color, color: active ? agent.color : undefined }}
            >
              <agent.icon className="size-4 text-white" />
              {state.status === 'done' && (
                <span className="absolute -right-1 -top-1 grid size-4 place-items-center rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900">
                  <Check className="size-2.5 text-white" strokeWidth={3} />
                </span>
              )}
              {state.status === 'failed' && (
                <span className="absolute -right-1 -top-1 grid size-4 place-items-center rounded-full bg-rose-500 ring-2 ring-white dark:ring-slate-900">
                  <AlertTriangle className="size-2.5 text-white" strokeWidth={3} />
                </span>
              )}
            </span>
            <span className="mt-1.5 min-w-0 sm:mt-0">
              <span className="block text-xs font-semibold sm:text-sm">{agent.name}</span>
              <span className={clsx('hidden truncate text-[11px] sm:block', active ? 'font-medium' : 'text-slate-500 dark:text-slate-400')} style={active ? { color: agent.color } : undefined}>
                {busy ? activity[agent.name] ?? (state.status === 'waiting' ? 'Waiting on specialists' : 'Standing by') : agent.role}
              </span>
            </span>
          </div>
        )
      })}
    </div>
  )
}
