export const fmtDate = (iso?: string) =>
  iso ? new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : '—'

export const fmtQuarter = (isoDate: string) => {
  const d = new Date(isoDate + 'T00:00:00')
  return `Q${Math.floor(d.getMonth() / 3) + 1} ${String(d.getFullYear()).slice(2)}`
}

export const fmtNumber = (value: unknown) =>
  typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(value ?? '—')

export const duration = (start?: string, end?: string) => {
  if (!start || !end) return '—'
  const seconds = (new Date(end).getTime() - new Date(start).getTime()) / 1000
  return seconds < 60 ? `${seconds.toFixed(1)}s` : `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

export const STATE_TONE: Record<string, 'green' | 'amber' | 'red' | 'blue' | 'slate'> = {
  complete: 'green',
  accept: 'green',
  supported: 'green',
  unverified: 'amber',
  partial: 'amber',
  needs_clarification: 'amber',
  revise: 'amber',
  running: 'blue',
  failed: 'red',
  cancelled: 'slate',
}
