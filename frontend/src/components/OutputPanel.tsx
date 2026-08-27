import { Download, FileText, CheckCircle2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import type { OutputFile } from '../lib/api'

interface OutputPanelProps {
  finalAnswer: string | null
  files: OutputFile[]
  isDone: boolean
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function OutputPanel({ finalAnswer, files, isDone }: OutputPanelProps) {
  return (
    <div className="space-y-4">
      {/* Files */}
      {files.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-border">
            <h3 className="text-sm font-medium text-white">Output Files</h3>
          </div>
          <div className="divide-y divide-border">
            {files.map((file) => (
              <div key={file.id} className="flex items-center gap-3 px-4 py-3">
                <div className="w-8 h-8 bg-green-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText className="w-4 h-4 text-green-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">{file.filename}</div>
                  <div className="text-xs text-muted">{formatBytes(file.size_bytes)}</div>
                </div>
                <a
                  href={file.download_url}
                  download={file.filename}
                  className="p-1.5 rounded-lg hover:bg-white/5 text-muted hover:text-white transition-colors"
                >
                  <Download className="w-4 h-4" />
                </a>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Final answer */}
      {finalAnswer && isDone && (
        <div className="card overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
            <CheckCircle2 className="w-4 h-4 text-green-400" />
            <h3 className="text-sm font-medium text-white">Final Answer</h3>
          </div>
          <div className="px-4 py-4">
            <div className="prose prose-sm prose-invert max-w-none">
              <ReactMarkdown
                components={{
                  code: ({ node, className, children, ...props }) => {
                    const isBlock = className?.includes('language-')
                    return isBlock ? (
                      <pre className="bg-black/40 rounded-lg p-3 overflow-x-auto">
                        <code className="text-xs font-mono text-gray-300">{children}</code>
                      </pre>
                    ) : (
                      <code className="bg-black/30 px-1.5 py-0.5 rounded text-xs font-mono text-amber-300">
                        {children}
                      </code>
                    )
                  },
                  p: ({ children }) => (
                    <p className="text-sm text-gray-300 leading-relaxed mb-3 last:mb-0">{children}</p>
                  ),
                  h1: ({ children }) => <h1 className="text-lg font-semibold text-white mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-semibold text-white mb-2">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-semibold text-white mb-1">{children}</h3>,
                  ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-3">{children}</ol>,
                  li: ({ children }) => <li className="text-sm text-gray-300">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                  table: ({ children }) => (
                    <div className="overflow-x-auto mb-3">
                      <table className="text-xs w-full border-collapse">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-border px-3 py-1.5 bg-surface text-left text-white font-medium">{children}</th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-border px-3 py-1.5 text-gray-300">{children}</td>
                  ),
                }}
              >
                {finalAnswer}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
