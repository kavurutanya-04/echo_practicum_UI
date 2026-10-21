import clsx from 'clsx'
import { useEffect, useRef, useState } from 'react'
import { agentByName } from '../../lib/agents'
import type { LogEvent } from '../../lib/api'
import { describe } from '../../lib/events'

const TONE_DOT = { info: 'bg-indigo-500', good: 'bg-emerald-500', bad: 'bg-rose-500', muted: 'bg-slate-300 dark:bg-slate-600' }

/** Scrolling, filterable list of execution-log events. */
export default function Timeline({ events, live }: { events: LogEvent[]; live: boolean }) {
  const [verbose, setVerbose] = useState(false)
  const list = useRef<HTMLOListElement>(null)
  const shown = verbose ? events : events.filter((e) => !['agent_turn', 'tool_request', 'model_started'].includes(e.event))

  useEffect(() => {
    // Scroll only the event list, never the page, while events stream in.
    if (live && list.current) list.current.scrollTop = list.current.scrollHeight
  }, [shown.length, live])

  return (
    <div>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-2 text-xs text-slate-500 dark:border-slate-800">
        <span>
          {shown.length} of {events.length} events
        </span>
        <label className="flex cursor-pointer items-center gap-1.5">
          <input type="checkbox" checked={verbose} onChange={(e) => setVerbose(e.target.checked)} className="accent-indigo-600" />
          Show every step
        </label>
      </div>
      <ol ref={list} className="max-h-[420px] overflow-y-auto px-5 py-3">
        {shown.map((event, index) => {
          const info = describe(event)
          const agent = agentByName(event.agent)
          return (
            <li key={index} className="slide-in flex gap-3 py-1.5 text-sm">
              <span className="w-12 shrink-0 pt-0.5 text-right font-mono text-[11px] text-slate-400">{event.elapsed_seconds.toFixed(1)}s</span>
              <span className={clsx('mt-1.5 size-2 shrink-0 rounded-full', TONE_DOT[info.tone])} />
              <span className="min-w-0">
                {agent && (
                  <span className="mr-1.5 rounded-md px-1.5 py-0.5 text-[11px] font-semibold text-white" style={{ background: agent.color }}>
                    {agent.name}
                  </span>
                )}
                <span className={clsx(info.tone === 'muted' && 'text-slate-500 dark:text-slate-400', info.tone === 'bad' && 'text-rose-600 dark:text-rose-400')}>
                  {info.text}
                </span>
              </span>
            </li>
          )
        })}
        {live && (
          <li className="flex items-center gap-3 py-1.5 text-sm text-slate-400">
            <span className="w-12" />
            <span className="size-2 animate-ping rounded-full bg-indigo-400" /> Waiting for the next step…
          </li>
        )}
      </ol>
    </div>
  )
}
