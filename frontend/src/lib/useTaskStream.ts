import { useEffect, useRef, useState } from 'react'
import type { AgentEvent } from './api'

export interface UseTaskStreamResult {
  events: AgentEvent[]
  isStreaming: boolean
  isDone: boolean
  error: string | null
}

export function useTaskStream(taskId: string | null): UseTaskStreamResult {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isDone, setIsDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!taskId) return

    // Reset state when task changes
    setEvents([])
    setIsStreaming(true)
    setIsDone(false)
    setError(null)

    const es = new EventSource(`/api/v1/tasks/${taskId}/stream`)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const event: AgentEvent = JSON.parse(e.data)
        setEvents((prev) => [...prev, event])

        if (event.event_type === 'done' || event.event_type === 'error') {
          setIsDone(true)
          setIsStreaming(false)
          es.close()
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err)
      }
    }

    es.onerror = () => {
      setIsStreaming(false)
      setError('Stream connection lost')
      es.close()
    }

    return () => {
      es.close()
      setIsStreaming(false)
    }
  }, [taskId])

  return { events, isStreaming, isDone, error }
}
