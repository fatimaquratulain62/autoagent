import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Send, Paperclip, X, ChevronDown, ChevronRight,
  Zap, Globe, Code2, Brain, AlertTriangle,
} from 'lucide-react'
import { Api } from '../lib/api'
import { useAppStore, ALL_TOOLS, PROVIDER_MODELS } from '../lib/store'

const EXAMPLE_TASKS = [
  "Compare the top 3 Python HTTP libraries: requests, httpx, and aiohttp. Get their GitHub stars, last commit date, and write a markdown comparison table.",
  "Search for the latest news about OpenAI and summarize the 5 most important developments from the past week.",
  "Write a Python script that generates Fibonacci numbers up to n=50, compute mean/median/sum, save results to a CSV file.",
  "Find the OpenWeatherMap API docs, show how to make a request, and write example Python code to get weather for London.",
]

const CAPABILITIES = [
  { icon: Globe,  label: 'Web Search & Browse', desc: 'Real-time search + full page reading' },
  { icon: Code2,  label: 'Python Execution',    desc: 'Run code, process data, call APIs' },
  { icon: Brain,  label: 'Multi-step Reasoning',desc: 'Autonomous ReAct loop, up to 20 turns' },
  { icon: Zap,    label: 'File Deliverables',   desc: 'Produce downloadable reports & data' },
]

export function HomePage() {
  const navigate = useNavigate()
  const { sessionId, defaultConfig, setDefaultConfig } = useAppStore()
  const [task, setTask]             = useState('')
  const [files, setFiles]           = useState<File[]>([])
  const [showConfig, setShowConfig] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError]           = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFiles = (newFiles: FileList | null) => {
    if (!newFiles) return
    setFiles(prev => [...prev, ...Array.from(newFiles)])
  }
  const removeFile = (i: number) =>
    setFiles(prev => prev.filter((_, idx) => idx !== i))

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    handleFiles(e.dataTransfer.files)
  }, [])

  const handleSubmit = async () => {
    if (!task.trim() || isSubmitting) return
    setIsSubmitting(true)
    setError('')
    try {
      const uploadedPaths: string[] = []
      for (const file of files) {
        const result = await Api.uploadFile(file, sessionId)
        uploadedPaths.push(result.path)
      }
      const { task_id } = await Api.startTask({
        description: task.trim(),
        config: defaultConfig,
        uploaded_file_paths: uploadedPaths,
      })
      navigate(`/task/${task_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setIsSubmitting(false)
    }
  }

  const toggleTool = (toolId: string) => {
    const enabled = defaultConfig.enabled_tools
    setDefaultConfig({
      enabled_tools: enabled.includes(toolId)
        ? enabled.filter(t => t !== toolId)
        : [...enabled, toolId],
    })
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero */}
      <div className="border-b border-border bg-gradient-to-b from-accent/5 to-transparent px-8 py-12">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-accent/10 border border-accent/20 text-accent text-xs font-medium px-3 py-1.5 rounded-full mb-5">
            <span className="live-dot w-1.5 h-1.5 bg-accent rounded-full" />
            Groq · {defaultConfig.model}
          </div>
          <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">
            What should I accomplish today?
          </h1>
          <p className="text-gray-400 text-lg">
            Describe any complex task — I'll autonomously plan, search, code, and execute until it's done.
          </p>
        </div>
      </div>

      <div className="flex-1 px-8 py-8">
        <div className="max-w-3xl mx-auto space-y-4">

          {/* Capabilities */}
          <div className="grid grid-cols-4 gap-3">
            {CAPABILITIES.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="card p-3">
                <Icon className="w-4 h-4 text-accent mb-1.5" />
                <div className="text-xs font-medium text-white">{label}</div>
                <div className="text-xs text-muted mt-0.5">{desc}</div>
              </div>
            ))}
          </div>

          {/* Task input */}
          <div
            onDrop={onDrop}
            onDragOver={e => e.preventDefault()}
            className="card overflow-hidden focus-within:border-accent/50 transition-colors"
          >
            <textarea
              value={task}
              onChange={e => setTask(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit()
              }}
              placeholder="Describe your task… (Ctrl+Enter to submit)"
              rows={5}
              className="w-full bg-transparent text-white placeholder-muted p-4 resize-none focus:outline-none text-sm leading-relaxed"
            />

            {files.length > 0 && (
              <div className="px-4 pb-2 flex flex-wrap gap-2">
                {files.map((f, i) => (
                  <div key={i} className="flex items-center gap-1.5 bg-white/5 border border-border rounded-full px-2.5 py-1 text-xs text-gray-300">
                    <Paperclip className="w-3 h-3 text-muted" />
                    {f.name}
                    <button onClick={() => removeFile(i)}><X className="w-3 h-3" /></button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center gap-3 px-4 py-3 border-t border-border bg-surface/50">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="text-muted hover:text-white transition-colors"
              >
                <Paperclip className="w-4 h-4" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={e => handleFiles(e.target.files)}
              />
              <span className="text-xs text-muted">{task.length} chars</span>
              <div className="ml-auto">
                <button
                  onClick={handleSubmit}
                  disabled={!task.trim() || isSubmitting}
                  className="btn-primary flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  {isSubmitting ? 'Starting…' : 'Run Task'}
                </button>
              </div>
            </div>
          </div>

          {/* Error — only shows on actual submit failure */}
          {error && (
            <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
              <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-red-400 font-medium">Failed to start task</p>
                <p className="text-xs text-red-300/80 mt-0.5 font-mono break-all">{error}</p>
              </div>
            </div>
          )}

          {/* Config panel */}
          <div className="card overflow-hidden">
            <button
              onClick={() => setShowConfig(!showConfig)}
              className="flex items-center gap-2 w-full px-4 py-3 text-left hover:bg-white/3 transition-colors"
            >
              {showConfig
                ? <ChevronDown className="w-4 h-4 text-muted" />
                : <ChevronRight className="w-4 h-4 text-muted" />}
              <span className="text-sm font-medium text-white">Advanced Configuration</span>
              <span className="ml-auto text-xs text-muted">
                {defaultConfig.llm_provider} · {defaultConfig.model} · {defaultConfig.max_turns} turns
              </span>
            </button>

            {showConfig && (
              <div className="px-4 pb-4 border-t border-border pt-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-muted mb-1.5 block">Provider</label>
                    <select
                      value={defaultConfig.llm_provider}
                      onChange={e => {
                        const p = e.target.value
                        setDefaultConfig({ llm_provider: p, model: PROVIDER_MODELS[p]?.[0] ?? '' })
                      }}
                      className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent"
                    >
                      <option value="groq">Groq</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted mb-1.5 block">
                      Model
                      {defaultConfig.llm_provider === 'groq' &&
                        <span className="ml-1 text-green-400/70"> (all Groq-hosted)</span>}
                    </label>
                    <select
                      value={defaultConfig.model}
                      onChange={e => setDefaultConfig({ model: e.target.value })}
                      className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent font-mono"
                    >
                      {(PROVIDER_MODELS[defaultConfig.llm_provider] ?? []).map(m => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted mb-1.5 flex justify-between">
                    <span>Max Turns</span>
                    <span className="text-white font-mono">{defaultConfig.max_turns}</span>
                  </label>
                  <input
                    type="range" min={1} max={30}
                    value={defaultConfig.max_turns}
                    onChange={e => setDefaultConfig({ max_turns: parseInt(e.target.value) })}
                    className="w-full accent-indigo-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-muted mb-2 block">Enabled Tools</label>
                  <div className="flex flex-wrap gap-2">
                    {ALL_TOOLS.map(tool => {
                      const on = defaultConfig.enabled_tools.includes(tool.id)
                      return (
                        <button
                          key={tool.id}
                          onClick={() => toggleTool(tool.id)}
                          className={`text-xs font-mono px-2.5 py-1 rounded-full border transition-colors ${
                            on
                              ? 'bg-accent/15 border-accent/30 text-accent'
                              : 'border-border text-muted hover:border-white/20 hover:text-white'
                          }`}
                        >
                          {tool.label}
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Examples */}
          <div>
            <p className="text-xs text-muted mb-3 uppercase tracking-wide font-medium">Try an example</p>
            <div className="grid grid-cols-2 gap-2">
              {EXAMPLE_TASKS.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setTask(ex)}
                  className="text-left p-3 rounded-lg border border-border hover:border-accent/30 hover:bg-accent/5 transition-colors group"
                >
                  <p className="text-xs text-gray-400 group-hover:text-gray-300 line-clamp-3 leading-relaxed">
                    {ex}
                  </p>
                </button>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}