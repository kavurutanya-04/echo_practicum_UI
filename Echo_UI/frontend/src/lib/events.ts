import { useEffect, useRef, useState } from 'react'
import type { LogEvent, RunMeta } from './api'
import type { AgentName } from './agents'

/** Subscribe to a run's execution log over server-sent events. */
export function useRunEvents(runId: string | undefined, paceMs: number, replayKey: number) {
  const [events, setEvents] = useState<LogEvent[]>([])
  const [done, setDone] = useState<RunMeta | null>(null)
  const [connected, setConnected] = useState(false)
  const source = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!runId) return
    setEvents([])
    setDone(null)
    const stream = new EventSource(`/api/runs/${runId}/events?pace_ms=${paceMs}`)
    source.current = stream
    stream.onopen = () => setConnected(true)
    stream.addEventListener('log', (message) => {
      try {
        const event = JSON.parse((message as MessageEvent).data) as LogEvent
        setEvents((current) => [...current, event])
      } catch {
        /* ignore malformed lines */
      }
    })
    stream.addEventListener('done', (message) => {
      setDone(JSON.parse((message as MessageEvent).data))
      stream.close()
      setConnected(false)
    })
    stream.onerror = () => setConnected(false)
    return () => stream.close()
  }, [runId, paceMs, replayKey])

  return { events, done, connected }
}

export type AgentState = { status: 'idle' | 'active' | 'waiting' | 'done' | 'failed'; calls: number; tools: number; failures: number }

/** Derive each agent's state from the event stream. */
export function agentStates(events: LogEvent[]): Record<AgentName, AgentState> {
  const states = Object.fromEntries(
    (['Original', 'Cherry', 'Vanilla', 'Lime', 'ZeroSugar'] as AgentName[]).map((name) => [name, { status: 'idle', calls: 0, tools: 0, failures: 0 }]),
  ) as Record<AgentName, AgentState>
  let current: AgentName | null = null
  for (const event of events) {
    const name = normalize(event.agent)
    if (!name) continue
    const state = states[name]
    if (event.event === 'model_started' || event.event === 'agent_started' || event.event === 'tool_started') {
      // Original coordinates the whole run, so it waits on specialists rather than finishing.
      if (current && current !== name && states[current].status === 'active') states[current].status = current === 'Original' ? 'waiting' : 'done'
      state.status = 'active'
      current = name
    }
    if (event.event === 'model_finished') state.calls += 1
    if (event.event === 'tool_finished') state.tools += 1
    if (event.event === 'model_failed' || event.event === 'agent_failed' || event.event === 'tool_failed') {
      state.failures += 1
      state.status = 'failed'
    }
    if (event.event === 'agent_finished' && state.status !== 'failed') state.status = 'done'
    if ((event.event === 'verification_finished' || event.event === 'visual_plan_validated') && state.status !== 'failed') state.status = 'done'
  }
  const finished = events.some((event) => event.event === 'run_finished')
  if (finished) for (const state of Object.values(states)) if (state.status === 'active' || state.status === 'waiting') state.status = 'done'
  return states
}

function normalize(agent?: string): AgentName | null {
  const map: Record<string, AgentName> = { original: 'Original', cherry: 'Cherry', vanilla: 'Vanilla', lime: 'Lime', zerosugar: 'ZeroSugar' }
  return agent ? map[agent.toLowerCase()] ?? null : null
}

const pretty = (value: unknown) => String(value ?? '').replace(/_/g, ' ')

/** Human-readable description of one execution-log event. */
export function describe(event: LogEvent): { text: string; tone: 'info' | 'good' | 'bad' | 'muted' } {
  const e = event
  switch (e.event) {
    case 'run_started':
      return { text: `Run started (${pretty(e.mode)})`, tone: 'info' }
    case 'scope_ready':
      return { text: `Scope fixed to ${e.manager_id}, ${e.start_date} → ${e.end_date}`, tone: 'muted' }
    case 'workflow_plan': {
      const needs = [e.needs_numbers && 'numbers', e.needs_text && 'comments', e.include_chart && 'a chart'].filter(Boolean).join(', ')
      return { text: `Plan: needs ${needs || 'no specialists'}${e.needs_clarification ? ' · asks for clarification' : ''}`, tone: 'info' }
    }
    case 'model_started':
      return { text: `Calling model${e.profile ? ` (${e.profile})` : ''}`, tone: 'muted' }
    case 'model_finished':
      return { text: e.tools && (e.tools as string[]).length ? `Model chose ${(e.tools as string[]).join(', ')}` : 'Model replied', tone: 'muted' }
    case 'model_failed':
      return { text: `Model call failed: ${pretty(e.error_category)}${e.http_status ? ` (HTTP ${e.http_status})` : ''}`, tone: 'bad' }
    case 'tool_started':
      return { text: `Running tool ${e.tool}`, tone: 'info' }
    case 'tool_finished':
      return { text: `Tool ${e.tool ?? ''} finished`, tone: 'muted' }
    case 'tool_failed':
    case 'tool_validation_failed':
      return { text: `Tool ${e.tool ?? ''} rejected: ${pretty(e.error_category ?? e.reason)}`, tone: 'bad' }
    case 'agent_started':
      return { text: 'Agent started', tone: 'info' }
    case 'agent_finished':
      return { text: 'Agent finished', tone: 'good' }
    case 'agent_failed':
      return { text: `Agent failed: ${pretty(e.error_category)}`, tone: 'bad' }
    case 'sentiment_batch_started':
      return { text: `Sentiment batch ${e.batch}/${e.batches} (${e.comments} comments)`, tone: 'info' }
    case 'visual_plan_validated':
      return { text: `Chart plan validated (${e.charts} chart${e.charts === 1 ? '' : 's'})`, tone: 'good' }
    case 'finding_reviewed':
      return { text: `Finding ${e.finding_id}: ${pretty(e.status)}`, tone: e.status === 'supported' ? 'good' : 'bad' }
    case 'verification_finished':
      return { text: `Review decision: ${e.decision}`, tone: e.decision === 'accept' ? 'good' : 'bad' }
    case 'repair_requested':
      return { text: 'Reviewer requested a revision', tone: 'bad' }
    case 'response_finished':
      return { text: `Response ${e.status}`, tone: e.status === 'complete' ? 'good' : 'bad' }
    case 'workflow_failed':
      return { text: `Workflow stopped: ${pretty(e.error_category)}${e.http_status ? ` (HTTP ${e.http_status})` : ''}`, tone: 'bad' }
    case 'run_finished':
      return { text: `Run finished${e.status ? ` · ${e.status}` : ''}`, tone: e.status === 'failed' ? 'bad' : 'good' }
    case 'run_cancelled':
      return { text: 'Run cancelled', tone: 'bad' }
    default:
      return { text: pretty(e.event), tone: 'muted' }
  }
}
