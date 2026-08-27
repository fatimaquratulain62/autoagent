import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search, Clock, CheckCircle2, XCircle, AlertCircle, Loader2, Calendar } from 'lucide-react'
import { Api } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'

const STATUS_ICONS: Record<string, React.ElementType> = {
  completed: CheckCircle2,
  failed: XCircle,
  cancelled: AlertCircle,
  running: Loader2,
  queued: Clock,
}

const STATUS_COLORS: Record<string, string> = {
  completed: 'text-green-400',
  failed: 'text-red-400',
  cancelled: 'text-gray-400',
  running: 'text-accent',
  queued: 'text-yellow-400',
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  if (seconds < 60) return `${Math.floor(seconds)}s`
  return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`
}

export function HistoryPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['history', search, statusFilter, page],
    queryFn: () => Api.getHistory({ search, status: statusFilter || undefined, page }),
  })

  const statuses = ['', 'completed', 'running', 'failed', 'cancelled', 'queued']

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">Task History</h1>
        <p className="text-sm text-muted mt-1">View and replay past agent tasks</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search tasks..."
            className="w-full bg-surface border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-accent placeholder-muted"
          />
        </div>

        <div className="flex items-center gap-1.5">
          {statuses.map(s => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(1) }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-accent text-white'
                  : 'text-muted hover:text-white border border-border hover:border-white/20'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-accent animate-spin" />
          </div>
        ) : !data?.items?.length ? (
          <div className="text-center py-12">
            <Calendar className="w-10 h-10 text-muted mx-auto mb-3" />
            <p className="text-sm text-muted">No tasks found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Task</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Turns</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.items.map(task => {
                const Icon = STATUS_ICONS[task.status] || Clock
                const color = STATUS_COLORS[task.status] || 'text-muted'
                return (
                  <tr
                    key={task.id}
                    onClick={() => navigate(`/task/${task.id}`)}
                    className="hover:bg-white/3 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <p className="text-sm text-white line-clamp-2 max-w-lg">{task.description}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className={`flex items-center gap-1.5 text-xs font-medium ${color}`}>
                        <Icon className={`w-3.5 h-3.5 ${task.status === 'running' ? 'animate-spin' : ''}`} />
                        {task.status}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-white font-mono">{task.turn_count}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-muted font-mono">
                        {formatDuration(task.duration_seconds)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-muted">
                        {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {data && data.items.length >= 20 && (
        <div className="flex items-center justify-between mt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-ghost disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-muted">Page {page}</span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={data.items.length < 20}
            className="btn-ghost disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
