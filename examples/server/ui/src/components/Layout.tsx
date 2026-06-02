import { Building2, KeyRound, ShieldCheck } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Organizations', icon: Building2, exact: true },
  { to: '/verify', label: 'Verify Key', icon: ShieldCheck, exact: false },
]

function getBreadcrumb(pathname: string) {
  if (pathname === '/') return [{ label: 'Organizations' }]
  if (pathname.startsWith('/orgs/')) return [{ label: 'Organizations', to: '/' }, { label: 'Org Details' }]
  if (pathname.startsWith('/projects/')) return [{ label: 'Organizations', to: '/' }, { label: 'Project Keys' }]
  if (pathname === '/verify') return [{ label: 'Verify Key' }]
  return []
}

export default function Layout() {
  const { pathname } = useLocation()
  const crumbs = getBreadcrumb(pathname)

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-[#dadce0] flex flex-col shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-4 h-14 border-b border-[#dadce0]">
          <div className="w-7 h-7 bg-[#1a73e8] rounded flex items-center justify-center">
            <KeyRound size={15} className="text-white" />
          </div>
          <div>
            <div className="text-[13px] font-medium text-[#202124] leading-tight">API Keys</div>
            <div className="text-[10px] text-[#5f6368]">Platform</div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2 overflow-y-auto">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              className={({ isActive }) =>
                `flex items-center gap-3 mx-2 px-3 py-2.5 rounded text-sm transition-colors ${
                  isActive
                    ? 'bg-[#e8f0fe] text-[#1a73e8] font-medium'
                    : 'text-[#3c4043] hover:bg-[#f1f3f4]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon size={16} className={isActive ? 'text-[#1a73e8]' : 'text-[#5f6368]'} />
                  {item.label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-[#dadce0]">
          <div className="text-[11px] text-[#9aa0a6]">SDK v1.0 · No auth</div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-[#dadce0] flex items-center px-6 gap-2 shrink-0">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-2">
              {i > 0 && <span className="text-[#9aa0a6] text-sm">/</span>}
              {c.to ? (
                <NavLink to={c.to} className="text-sm text-[#1a73e8] hover:underline">{c.label}</NavLink>
              ) : (
                <span className="text-sm text-[#202124] font-medium">{c.label}</span>
              )}
            </span>
          ))}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
