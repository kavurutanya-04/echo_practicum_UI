import { BarChart3, Database, MessageSquareText, ShieldCheck, Workflow, type LucideIcon } from 'lucide-react'

export type AgentName = 'Original' | 'Cherry' | 'Vanilla' | 'Lime' | 'ZeroSugar'

export const AGENTS: { name: AgentName; role: string; detail: string; color: string; icon: LucideIcon }[] = [
  { name: 'Original', role: 'Coordinator', detail: 'Plans the work, delegates and writes the cited answer.', color: 'var(--color-original)', icon: Workflow },
  { name: 'Cherry', role: 'Text-to-SQL', detail: 'Turns questions into scoped SQL over the HR and operations tables.', color: 'var(--color-cherry)', icon: Database },
  { name: 'Vanilla', role: 'Text RAG & sentiment', detail: 'Retrieves anonymous comments and labels survey sentiment.', color: 'var(--color-vanilla)', icon: MessageSquareText },
  { name: 'Lime', role: 'Charts', detail: 'Chooses evidence-bound charts, or explains why none fits.', color: 'var(--color-lime)', icon: BarChart3 },
  { name: 'ZeroSugar', role: 'Reviewer', detail: 'Checks citations, scope, SQL replay and rates the answer.', color: 'var(--color-zerosugar)', icon: ShieldCheck },
]

export const agentByName = (name?: string) =>
  AGENTS.find((agent) => agent.name.toLowerCase() === (name ?? '').toLowerCase())

// Pastel chart colours (deep enough for projectors), starting with the sage and mist-blue palette colours. Power BI exports use the same list. Each series (or each bar of a one-series bar chart) takes the next one.
export const SERIES_COLORS = ['#8fa066', '#7f97b5', '#d98a99', '#e0a267', '#9c8fcb', '#6fb39a', '#d2b356', '#78a9cf']
