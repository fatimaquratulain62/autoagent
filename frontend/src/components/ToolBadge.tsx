import { Search, Globe, Code, FileText, Upload, Network, Database } from 'lucide-react'

const TOOL_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  web_search: { icon: Search, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  browse_url: { icon: Globe, color: 'text-teal-400', bg: 'bg-teal-500/10 border-teal-500/20' },
  run_python: { icon: Code, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
  read_file: { icon: FileText, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
  write_file: { icon: Upload, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
  http_request: { icon: Network, color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' },
  memory_store: { icon: Database, color: 'text-pink-400', bg: 'bg-pink-500/10 border-pink-500/20' },
  memory_retrieve: { icon: Database, color: 'text-pink-400', bg: 'bg-pink-500/10 border-pink-500/20' },
}

const DEFAULT_CONFIG = { icon: Code, color: 'text-gray-400', bg: 'bg-gray-500/10 border-gray-500/20' }

interface ToolBadgeProps {
  toolName: string
  size?: 'sm' | 'md'
}

export function ToolBadge({ toolName, size = 'md' }: ToolBadgeProps) {
  const config = TOOL_CONFIG[toolName] || DEFAULT_CONFIG
  const Icon = config.icon

  return (
    <span
      className={`inline-flex items-center gap-1.5 border rounded-full font-mono font-medium ${config.bg} ${config.color} ${
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-xs'
      }`}
    >
      <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      {toolName}
    </span>
  )
}
