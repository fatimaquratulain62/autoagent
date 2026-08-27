import { create } from 'zustand'
import type { HarnessConfig } from './api'

interface AppStore {
  // Current session for file uploads
  sessionId: string
  setSessionId: (id: string) => void

  // Default harness config (user preferences)
  defaultConfig: HarnessConfig
  setDefaultConfig: (config: Partial<HarnessConfig>) => void
}

const DEFAULT_CONFIG: HarnessConfig = {
  max_turns: 40,
  total_token_budget: 100000,
  llm_provider: 'groq',
  // Groq model ID (matches Groq Playground)
  model: 'openai/gpt-oss-120b',
  enabled_tools: [
    'web_search',
    'browse_url',
    'run_python',
    'read_file',
    'write_file',
    'http_request',
    'memory_store',
    'memory_retrieve',
  ],
}

// Models available per provider (for the dropdown)
export const PROVIDER_MODELS: Record<string, string[]> = {
  groq: [
    'openai/gpt-oss-120b',
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'mixtral-8x7b-32768',
    'gemma2-9b-it',
  ],
  openai: [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4-turbo',
  ],
  anthropic: [
    'claude-opus-4-6',
    'claude-sonnet-4-6',
    'claude-haiku-4-5-20251001',
  ],
}

export const useAppStore = create<AppStore>((set) => ({
  sessionId: crypto.randomUUID(),
  setSessionId: (id) => set({ sessionId: id }),

  defaultConfig: DEFAULT_CONFIG,

  setDefaultConfig: (config) =>
    set((state) => ({
      defaultConfig: {
        ...state.defaultConfig,
        ...config,
      },
    })),
}))

export const ALL_TOOLS = [
  { id: 'web_search', label: 'Web Search', color: 'tool-search' },
  { id: 'browse_url', label: 'Browse URL', color: 'tool-browse' },
  { id: 'run_python', label: 'Run Python', color: 'tool-code' },
  { id: 'read_file', label: 'Read File', color: 'tool-file' },
  { id: 'write_file', label: 'Write File', color: 'tool-file' },
  { id: 'http_request', label: 'HTTP Request', color: 'tool-http' },
  { id: 'memory_store', label: 'Memory Store', color: 'tool-memory' },
  { id: 'memory_retrieve', label: 'Memory Retrieve', color: 'tool-memory' },
]