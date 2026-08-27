import { useState } from 'react'
import { ChevronDown, ChevronRight, Copy, CheckCheck, Brain, Wrench, Terminal } from 'lucide-react'
import type { AgentEvent } from '../lib/api'
import { ToolBadge } from './ToolBadge'

interface TurnCardProps {
  events: AgentEvent[]
  turnNumber: number
  isLive?: boolean
}

export function TurnCard({ events, turnNumber, isLive = false }: TurnCardProps) {
  const thought = events.find(e => e.event_type === 'thought')
  const toolCall = events.find(e => e.event_type === 'tool_call')
  const toolResult = events.find(e => e.event_type === 'tool_result')
  const error = events.find(e => e.event_type === 'error')

  const [showThought, setShowThought] = useState(true)
  const [showArgs, setShowArgs] = useState(false)
  const [showResult, setShowResult] = useState(false)
  const [copied, setCopied] = useState(false)

  const copyResult = () => {
    if (toolResult?.tool_result) {
      navigator.clipboard.writeText(toolResult.tool_result)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const totalTokens = thought?.token_usage?.total_tokens || 0
  const duration = (thought?.duration_ms || 0) + (toolResult?.duration_ms || 0)

  return (
    <div className={`card animate-slide-up ${error ? 'border-red-500/30' : ''}`}>
      {/* Turn header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
            error ? 'bg-red-500/20 text-red-400' :
            isLive ? 'bg-accent/20 text-accent' :
            'bg-white/5 text-muted'
          }`}>
            {turnNumber}
          </div>
          {toolCall && <ToolBadge toolName={toolCall.tool_name!} />}
          {isLive && !toolCall && (
            <span className="text-xs text-accent flex items-center gap-1.5">
              <span className="live-dot w-1.5 h-1.5 bg-accent rounded-full inline-block" />
              Thinking...
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted">
          {totalTokens > 0 && <span>{totalTokens.toLocaleString()} tok</span>}
          {duration > 0 && <span>{(duration / 1000).toFixed(1)}s</span>}
        </div>
      </div>

      {/* Thought section */}
      {thought?.content && (
        <div className="border-b border-border">
          <button
            onClick={() => setShowThought(!showThought)}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-left hover:bg-white/3 transition-colors"
          >
            <Brain className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
            <span className="text-xs font-medium text-indigo-400 uppercase tracking-wide">Thought</span>
            {showThought ? (
              <ChevronDown className="w-3.5 h-3.5 text-muted ml-auto" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-muted ml-auto" />
            )}
          </button>
          {showThought && (
            <div className="px-4 pb-3">
              <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                {thought.content}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tool call section */}
      {toolCall && (
        <div className="border-b border-border">
          <button
            onClick={() => setShowArgs(!showArgs)}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-left hover:bg-white/3 transition-colors"
          >
            <Wrench className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            <span className="text-xs font-medium text-amber-400 uppercase tracking-wide">Tool Call</span>
            <span className="ml-2 font-mono text-xs text-gray-400">{toolCall.tool_name}</span>
            {showArgs ? (
              <ChevronDown className="w-3.5 h-3.5 text-muted ml-auto" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-muted ml-auto" />
            )}
          </button>
          {showArgs && toolCall.tool_args && (
            <div className="px-4 pb-3">
              <pre className="bg-black/30 rounded-lg p-3 text-xs font-mono text-gray-300 overflow-x-auto">
                {JSON.stringify(toolCall.tool_args, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Tool result section */}
      {toolResult?.tool_result && (
        <div>
          <div className="flex items-center gap-2 px-4 py-2.5">
            <Terminal className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
            <button
              onClick={() => setShowResult(!showResult)}
              className="flex items-center gap-1.5 flex-1 text-left"
            >
              <span className="text-xs font-medium text-green-400 uppercase tracking-wide">Result</span>
              <span className="text-xs text-muted ml-2">
                ({toolResult.tool_result.length.toLocaleString()} chars)
              </span>
              {showResult ? (
                <ChevronDown className="w-3.5 h-3.5 text-muted ml-auto" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-muted ml-auto" />
              )}
            </button>
            <button
              onClick={copyResult}
              className="p-1 rounded hover:bg-white/10 transition-colors text-muted hover:text-white"
            >
              {copied ? (
                <CheckCheck className="w-3.5 h-3.5 text-green-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
          {showResult && (
            <div className="px-4 pb-3">
              <pre className="bg-black/30 rounded-lg p-3 text-xs font-mono text-gray-300 overflow-x-auto max-h-96 overflow-y-auto">
                {toolResult.tool_result}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-4 py-3 text-sm text-red-400 bg-red-500/5">
          {error.content}
        </div>
      )}
    </div>
  )
}
