import { XCircle, RotateCcw, Clock } from 'lucide-react'

interface StatusBarProps {
  status: string
  turnCount: number
  maxTurns: number
  totalTokens: number
  tokenBudget: number
  elapsedSeconds: number
  onCancel: () => void
  onResume: () => void
  isStreaming: boolean
}

const STATUS_COLORS: Record<string, string> = {
  queued: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  running: 'text-accent bg-accent/10 border-accent/20',
  completed: 'text-green-400 bg-green-500/10 border-green-500/20',
  failed: 'text-red-400 bg-red-500/10 border-red-500/20',
  cancelled: 'text-gray-400 bg-gray-500/10 border-gray-500/20',
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}m ${s}s`
}

export function StatusBar({
  status,
  turnCount,
  maxTurns,
  totalTokens,
  tokenBudget,
  elapsedSeconds,
  onCancel,
  onResume,
  isStreaming,
}: StatusBarProps) {
  const tokenPct = Math.min((totalTokens / tokenBudget) * 100, 100)
  const turnPct = Math.min((turnCount / maxTurns) * 100, 100)

  return (
    <div className="card p-4">
      <div className="flex items-center gap-4 flex-wrap">
        {/* Status badge */}
        <span className={`status-badge border ${STATUS_COLORS[status] || STATUS_COLORS.queued}`}>
          {isStreaming && (
            <span className="live-dot w-1.5 h-1.5 rounded-full bg-current inline-block" />
          )}
          {status}
        </span>

        {/* Turns */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">Turns</span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all"
                style={{ width: `${turnPct}%` }}
              />
            </div>
            <span className="text-xs text-white font-mono">{turnCount}/{maxTurns}</span>
          </div>
        </div>

        {/* Tokens */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">Tokens</span>
          <div className="flex items-center gap-2">
            <div className="w-20 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${tokenPct > 80 ? 'bg-red-400' : 'bg-green-400'}`}
                style={{ width: `${tokenPct}%` }}
              />
            </div>
            <span className="text-xs text-white font-mono">{totalTokens.toLocaleString()}</span>
          </div>
        </div>

        {/* Elapsed */}
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <Clock className="w-3.5 h-3.5" />
          {formatTime(elapsedSeconds)}
        </div>

        {/* Actions */}
        <div className="ml-auto flex items-center gap-2">
          {(status === 'failed' || status === 'cancelled') && (
            <button onClick={onResume} className="btn-ghost flex items-center gap-1.5">
              <RotateCcw className="w-3.5 h-3.5" />
              Resume
            </button>
          )}
          {(status === 'running' || status === 'queued') && (
            <button
              onClick={onCancel}
              className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 border border-red-500/20 hover:border-red-500/40 rounded-lg px-3 py-1.5 transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
