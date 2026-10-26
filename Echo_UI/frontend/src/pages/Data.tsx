import clsx from 'clsx'
import { Database, KeyRound, Link2, Search } from 'lucide-react'
import { useState } from 'react'
import { PageTitle } from '../components/Layout'
import { Badge, Card, CardHeader, ErrorNote, inputClass, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { useAsync } from '../lib/useAsync'

export default function Data() {
  const tables = useAsync(api.tables)
  const [active, setActive] = useState('HR_survey_summary')
  const [query, setQuery] = useState('')
  const table = tables.data?.find((t) => t.name === active) ?? tables.data?.[0]
  const columns = (table?.columns ?? []).filter((c) => `${c.Column} ${c.Meaning}`.toLowerCase().includes(query.toLowerCase()))

  return (
    <>
      <PageTitle title="Data" subtitle="The eleven tables Echo can reach, with the schema dictionary. Agents only ever see scoped, approved fields." />
      {tables.loading && !tables.data ? (
        <Spinner />
      ) : tables.error ? (
        <ErrorNote error={tables.error} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
          <Card className="h-fit">
            <ul className="p-2">
              {tables.data!.map((t) => (
                <li key={t.name}>
                  <button
                    onClick={() => setActive(t.name)}
                    className={clsx(
                      'flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition',
                      table?.name === t.name ? 'bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300' : 'hover:bg-slate-50 dark:hover:bg-slate-800/50',
                    )}
                  >
                    <span className="truncate font-mono text-xs">{t.name}</span>
                    <span className="text-xs tabular-nums text-slate-500">{t.rows.toLocaleString()}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          {table && (
            <Card>
              <CardHeader
                title={<span className="font-mono">{table.name}</span>}
                subtitle={`${table.rows.toLocaleString()} rows · ${table.columns.length} documented columns`}
                icon={Database}
                action={
                  <div className="relative w-56">
                    <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-400" />
                    <input className={clsx(inputClass, 'pl-9')} placeholder="Filter columns" value={query} onChange={(e) => setQuery(e.target.value)} />
                  </div>
                }
              />
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-slate-500">
                    <tr className="border-b border-slate-100 dark:border-slate-800">
                      <th className="px-5 py-2.5 font-medium">Column</th>
                      <th className="px-3 py-2.5 font-medium">Meaning</th>
                      <th className="px-3 py-2.5 font-medium">Keys</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {columns.map((c) => (
                      <tr key={c.Column}>
                        <td className="whitespace-nowrap px-5 py-2.5 font-mono text-xs">{c.Column}</td>
                        <td className="px-3 py-2.5 text-slate-600 dark:text-slate-300">{c.Meaning}</td>
                        <td className="px-3 py-2.5">
                          <div className="flex flex-wrap gap-1">
                            {c.Primary_Key === 'Yes' && (
                              <Badge tone="blue">
                                <KeyRound className="size-3" /> PK
                              </Badge>
                            )}
                            {c.References && (
                              <Badge>
                                <Link2 className="size-3" /> {c.References}
                              </Badge>
                            )}
                            {c.Nullable === 'Yes' && <Badge>nullable</Badge>}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </>
  )
}
