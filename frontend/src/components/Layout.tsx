import { Outlet, NavLink } from 'react-router-dom'
import { Bot, History, Calendar, Zap } from 'lucide-react'

export function Layout() {
  const navItems = [
    { to: '/', icon: Zap, label: 'New Task' },
    { to: '/history', icon: History, label: 'History' },
    { to: '/scheduled', icon: Calendar, label: 'Scheduled' },
  ]

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-surface border-r border-border flex flex-col fixed h-full z-10">
        {/* Logo */}
        <div className="p-5 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-semibold text-white text-sm">AutoAgent</div>
              <div className="text-xs text-muted">AI Task Engine</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-accent-dim text-accent'
                    : 'text-muted hover:text-white hover:bg-white/5'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <div className="text-xs text-muted">
            <div>ReAct Agent Loop</div>
            <div className="mt-0.5 text-[10px] opacity-60">Powered by Groq + Llama 3</div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 ml-56 min-h-screen">
        <Outlet />
      </main>
    </div>
  )
}
