import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Api } from '../lib/api'
import { useTaskStream } from '../lib/useTaskStream'
import { TurnCard } from '../components/TurnCard'
import { OutputPanel } from '../components/OutputPanel'
import { StatusBar } from '../components/StatusBar'
import type { AgentEvent } from '../lib/api'

// Group events by turn number
function groupByTurn(events: AgentEvent[]): Map<number, AgentEvent[]> {
  const map = new Map<number, AgentEvent[]>()
  for (const event of events) {
    if (!map.has(event.turn)) map.set(event.turn, [])
    map.get(event.turn)!.push(event)
  }
  return map
}

export function TaskPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [startTime] = useState(Date.now())
  const [elapsed, setElapsed] = useState(0)

  const { events, isStreaming, isDone } = useTaskStream(id ?? null)

  // Poll status
  const { data: status } = useQuery({
    queryKey: ['task-status', id],
    queryFn: () => Api.getTaskStatus(id!),
    refetchInterval: isDone ? false : 3000,
    enabled: !!id,
  })

  // Files
  const { data: files = [] } = useQuery({
    queryKey: ['task-files', id],
    queryFn: () => Api.getTaskFiles(id!),
    refetchInterval: isDone ? false : 5000,
    enabled: !!id,
  })

  // Cancel
  const cancelMutation = useMutation({
    mutationFn: () => Api.cancelTask(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['task-status', id] }),
  })

  // Resume
  const resumeMutation = useMutation({
    mutationFn: () => Api.resumeTask(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['task-status', id] })
      window.location.reload()
    },
  })

  // Elapsed timer
  useEffect(() => {
    if (isDone) return
    const t = setInterval(() => setElapsed((Date.now() - startTime) / 1000), 1000)
    return () => clearInterval(t)
  }, [isDone, startTime])

  // Auto-scroll
  useEffect(() => {
    if (isStreaming) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [events.length, isStreaming])

  const turnMap = groupByTurn(events)
  const turnNumbers = Array.from(turnMap.keys()).sort((a, b) => a - b)

  // Find final answer from done event
  const doneEvent = events.find(e => e.event_type === 'done')
  const finalAnswer = doneEvent?.content || status?.final_answer || null

  // Token total from events
  const totalTokens = events.reduce((sum, e) => {
    return sum + (e.token_usage?.total_tokens || 0)
  }, 0)

  const currentStatus = status?.status || 'queued'
  const maxTurns = status ? (JSON.parse(JSON.stringify({})).max_turns || 40) : 40

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar */}
      <div className="border-b border-border px-6 py-4 flex items-center gap-4 bg-surface/50">
        <button
          onClick={() => navigate('/')}
          className="text-muted hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-white font-medium truncate">
            {status?.description || 'Loading task...'}
          </p>
          {status?.created_at && (
            <p className="text-xs text-muted">
              Started {new Date(status.created_at).toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>

      {/* Status bar */}
      <div className="px-6 py-3 border-b border-border">
        <StatusBar
          status={currentStatus}
          turnCount={turnNumbers.length}
          maxTurns={40}
          totalTokens={totalTokens || status?.total_tokens || 0}
          tokenBudget={100000}
          elapsedSeconds={elapsed}
          onCancel={() => cancelMutation.mutate()}
          onResume={() => resumeMutation.mutate()}
          isStreaming={isStreaming}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Timeline */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {turnNumbers.length === 0 && !isDone && (
            <div className="text-center py-12">
              <div className="w-12 h-12 border-2 border-accent/30 border-t-accent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-muted">Agent is starting up...</p>
            </div>
          )}

          {turnNumbers.map((turn, idx) => {
            const turnEvents = turnMap.get(turn)!
            const isLastTurn = idx === turnNumbers.length - 1
            const isTurnLive = isLastTurn && isStreaming && !isDone

            return (
              <TurnCard
                key={turn}
                events={turnEvents}
                turnNumber={turn}
                isLive={isTurnLive}
              />
            )
          })}

          {/* Live thinking indicator when streaming but no events yet for this turn */}
          {isStreaming && !isDone && turnNumbers.length > 0 && (
            <div className="flex items-center gap-3 px-4 py-3 text-sm text-muted">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
              <span>Processing...</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Output panel */}
        {(files.length > 0 || finalAnswer) && (
          <div className="w-80 border-l border-border overflow-y-auto p-4 space-y-4 flex-shrink-0">
            <h2 className="text-sm font-semibold text-white">Outputs</h2>
            <OutputPanel
              finalAnswer={finalAnswer}
              files={files}
              isDone={isDone}
            />
          </div>
        )}
      </div>
    </div>
  )
}
