import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar, Plus, Trash2, ToggleLeft, ToggleRight, Clock, Loader2, X } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

const BASE = '/api/v1/scheduled'

async function getScheduled() {
  const res = await fetch(BASE)
  return res.json()
}

async function createScheduled(payload: { cron_expression: string; task_description: string }) {
  const res = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.json()
}

async function toggleScheduled(id: string, is_active: boolean) {
  const res = await fetch(`${BASE}/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active }),
  })
  return res.json()
}

async function deleteScheduled(id: string) {
  await fetch(`${BASE}/${id}`, { method: 'DELETE' })
}

const CRON_EXAMPLES = [
  { label: 'Every hour', value: '0 * * * *' },
  { label: 'Every day at 9am', value: '0 9 * * *' },
  { label: 'Every Monday at 8am', value: '0 8 * * 1' },
  { label: 'Every 5 minutes', value: '*/5 * * * *' },
]

export function ScheduledPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [cron, setCron] = useState('0 9 * * *')
  const [description, setDescription] = useState('')

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['scheduled'],
    queryFn: getScheduled,
  })

  const createMutation = useMutation({
    mutationFn: createScheduled,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scheduled'] })
      setShowForm(false)
      setCron('0 9 * * *')
      setDescription('')
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      toggleScheduled(id, is_active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scheduled'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteScheduled,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scheduled'] }),
  })

  const handleCreate = () => {
    if (!cron.trim() || !description.trim()) return
    createMutation.mutate({ cron_expression: cron, task_description: description })
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Scheduled Tasks</h1>
          <p className="text-sm text-muted mt-1">Run agent tasks on a recurring schedule</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2"
        >
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? 'Cancel' : 'Schedule Task'}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card p-5 mb-4 animate-slide-up">
          <h3 className="text-sm font-semibold text-white mb-4">New Scheduled Task</h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-muted mb-1.5 block">Cron Expression</label>
              <div className="flex items-center gap-2">
                <input
                  value={cron}
                  onChange={e => setCron(e.target.value)}
                  className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-accent"
                  placeholder="0 9 * * *"
                />
              </div>
              <div className="flex gap-2 mt-2">
                {CRON_EXAMPLES.map(ex => (
                  <button
                    key={ex.value}
                    onClick={() => setCron(ex.value)}
                    className="text-xs px-2 py-1 rounded border border-border text-muted hover:text-white hover:border-white/20 transition-colors font-mono"
                  >
                    {ex.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs text-muted mb-1.5 block">Task Description</label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                rows={3}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent resize-none"
                placeholder="What should the agent do each time this runs?"
              />
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleCreate}
                disabled={!cron.trim() || !description.trim() || createMutation.isPending}
                className="btn-primary"
              >
                {createMutation.isPending ? 'Scheduling...' : 'Create Schedule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tasks list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-accent animate-spin" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="card text-center py-12">
          <Calendar className="w-10 h-10 text-muted mx-auto mb-3" />
          <p className="text-sm text-white mb-1">No scheduled tasks</p>
          <p className="text-xs text-muted">Create a schedule to run tasks automatically</p>
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map((task: any) => (
            <div key={task.id} className={`card p-4 ${!task.is_active ? 'opacity-50' : ''}`}>
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs bg-accent/10 text-accent border border-accent/20 px-2 py-0.5 rounded">
                      {task.cron_expression}
                    </span>
                    <span className={`text-xs font-medium ${task.is_active ? 'text-green-400' : 'text-muted'}`}>
                      {task.is_active ? 'Active' : 'Paused'}
                    </span>
                  </div>
                  <p className="text-sm text-white line-clamp-2">{task.task_description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-muted">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {task.run_count} runs
                    </span>
                    {task.last_run && (
                      <span>Last run {formatDistanceToNow(new Date(task.last_run), { addSuffix: true })}</span>
                    )}
                    <span>Created {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => toggleMutation.mutate({ id: task.id, is_active: !task.is_active })}
                    className="text-muted hover:text-white transition-colors"
                  >
                    {task.is_active ? (
                      <ToggleRight className="w-5 h-5 text-accent" />
                    ) : (
                      <ToggleLeft className="w-5 h-5" />
                    )}
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Delete this scheduled task?')) {
                        deleteMutation.mutate(task.id)
                      }
                    }}
                    className="text-muted hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
