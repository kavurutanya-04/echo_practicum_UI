import clsx from 'clsx'
import { Database, History, LayoutDashboard, Menu, Moon, PlugZap, ShieldAlert, Sparkles, Sun, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { AGENTS } from '../lib/agents'

const NAV = [
  { to: '/console', label: 'Ask Echo', icon: Sparkles, end: true },
  { to: '/console/runs', label: 'Runs', icon: History },
  { to: '/console/dashboard', label: 'Team dashboard', icon: LayoutDashboard },
  { to: '/console/data', label: 'Data', icon: Database },
  { to: '/console/connections', label: 'Connections', icon: PlugZap },
]

export function useTheme() {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem('echo-theme')
      if (saved) return saved === 'dark'
    } catch {
      /* storage unavailable */
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try {
      localStorage.setItem('echo-theme', dark ? 'dark' : 'light')
    } catch {
      /* storage unavailable */
    }
  }, [dark])
  return [dark, setDark] as const
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <img src="/favicon.svg" alt="" className="size-8" />
        <div>
          <div className="text-sm font-semibold tracking-tight">Echo · Technical</div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400">Runs, evidence and connections</div>
        </div>
      </div>
      <nav className="flex flex-col gap-0.5 px-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition',
                isActive
                  ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800/60',
              )
            }
          >
            <Icon className="size-4" /> {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-6 px-5">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Agents</div>
        <ul className="space-y-1.5">
          {AGENTS.map((agent) => (
            <li key={agent.name} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400" title={agent.detail}>
              <span className="size-2 rounded-full" style={{ background: agent.color }} />
              <span className="font-medium text-slate-700 dark:text-slate-300">{agent.name}</span>
              <span className="truncate">· {agent.role}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-auto p-4">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-[11px] leading-relaxed text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/5 dark:text-amber-200">
          <div className="mb-1 flex items-center gap-1.5 font-semibold">
            <ShieldAlert className="size-3.5" /> Responsible use
          </div>
          All employee data is synthetic. Echo supports human review and does not make personnel decisions. Comments
          stay anonymous; groups under 5 responses are suppressed.
        </div>
      </div>
    </div>
  )
}

export default function Layout() {
  const [dark, setDark] = useTheme()
  const [open, setOpen] = useState(false)
  const location = useLocation()
  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  return (
    <div className="flex h-full">
      <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:block dark:border-slate-800 dark:bg-slate-900/60">
        <Sidebar />
      </aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-950/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
            <Sidebar onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white/80 px-4 py-2.5 backdrop-blur lg:px-8 dark:border-slate-800 dark:bg-slate-950/80">
          <button className="rounded-lg p-1.5 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800" onClick={() => setOpen(true)} aria-label="Open menu">
            {open ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
          <span className="text-xs text-slate-500 dark:text-slate-400">Technical console · local only</span>
          <NavLink to="/" className="ml-4 text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400">← Manager view</NavLink>
          <button
            onClick={() => setDark(!dark)}
            className="ml-auto rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Toggle theme"
          >
            {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-7xl px-4 py-6 lg:px-8 lg:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export function PageTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}
