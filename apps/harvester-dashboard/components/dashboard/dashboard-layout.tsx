'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Calendar,
  MapPin,
  Settings,
  Flame,
  CheckCheck,
  LogOut,
  User2,
  Users,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/components/providers/auth-provider'
import { RequireAuth } from '@/components/auth/require-auth'
import { RequireRole } from '@/components/auth/require-role'
import { MODERATOR_AND_ABOVE, hasAdminAccess } from '@/lib/auth'

const navItems = [
  { href: '/', label: 'Pending', icon: Calendar },
  { href: '/published', label: 'Published', icon: CheckCheck },
  { href: '/venues', label: 'Venues', icon: MapPin },
]

interface DashboardLayoutProps {
  children: React.ReactNode
}

const adminNavItem = { href: '/admin/users', label: 'Users', icon: Users }

function DashboardContent({ children }: DashboardLayoutProps) {
  const pathname = usePathname()
  const { fomoUser, oidcUser, logout } = useAuth()
  const isAdmin = hasAdminAccess(fomoUser?.system_role)

  const displayName =
    fomoUser?.username ??
    oidcUser?.profile?.preferred_username ??
    'User'

  return (
    <div className="flex h-screen bg-background selection:bg-neon-purple/30 selection:text-neon-purple">
      {/* Fixed Left Navigation */}
      <aside className="w-20 flex-shrink-0 panel-neon border-r border-border bg-sidebar flex flex-col items-center py-6 z-20">
        {/* Logo */}
        <div className="mb-10">
          <div className="w-12 h-12 rounded-2xl bg-primary neon-glow-blue flex items-center justify-center animate-neon-pulse">
            <Flame className="w-6 h-6 text-primary-foreground" />
          </div>
        </div>

        {/* Navigation — visible to moderator/manager/admin (all current pages are moderation routes) */}
        <nav className="flex flex-col gap-6">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 relative group',
                  isActive
                    ? 'bg-neon-blue/20 text-neon-blue neon-border-blue neon-glow-sm'
                    : 'text-muted-foreground hover:text-neon-blue hover:bg-neon-blue/10'
                )}
                title={item.label}
              >
                <item.icon className={cn(
                  "w-6 h-6 transition-transform duration-300 group-hover:scale-110",
                  isActive && "animate-neon-pulse"
                )} />
                {isActive && (
                  <span className="absolute -left-1 w-1 h-6 bg-neon-blue rounded-r-full shadow-[0_0_10px_var(--neon-blue)]" />
                )}
              </Link>
            )
          })}
          {isAdmin && (() => {
            const isActive = pathname === adminNavItem.href
            return (
              <Link
                href={adminNavItem.href}
                className={cn(
                  'w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 relative group',
                  isActive
                    ? 'bg-neon-purple/20 text-neon-purple neon-border-purple neon-glow-sm'
                    : 'text-muted-foreground hover:text-neon-purple hover:bg-neon-purple/10'
                )}
                title={adminNavItem.label}
              >
                <adminNavItem.icon className={cn(
                  "w-6 h-6 transition-transform duration-300 group-hover:scale-110",
                  isActive && "animate-neon-pulse"
                )} />
                {isActive && (
                  <span className="absolute -left-1 w-1 h-6 bg-neon-purple rounded-r-full shadow-[0_0_10px_var(--neon-purple)]" />
                )}
              </Link>
            )
          })()}
        </nav>

        {/* Bottom actions */}
        <div className="mt-auto flex flex-col gap-4 items-center">
          {/* User identity */}
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-muted-foreground bg-muted/20 transition-all duration-300"
            title={displayName}
          >
            <User2 className="w-5 h-5" />
          </div>

          {/* Settings */}
          <button
            className="w-12 h-12 rounded-xl flex items-center justify-center text-muted-foreground hover:text-neon-purple hover:bg-neon-purple/10 transition-all duration-300 group"
            title="Settings"
          >
            <Settings className="w-6 h-6 group-hover:rotate-45 transition-transform" />
          </button>

          {/* Logout */}
          <button
            onClick={logout}
            className="w-12 h-12 rounded-xl flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-300"
            title="Logout"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden relative bg-[radial-gradient(circle_at_20%_20%,rgba(37,99,235,0.08),transparent_40%),radial-gradient(circle_at_80%_80%,rgba(147,51,234,0.08),transparent_40%)]">
        {/* Subtle background noise/grid could go here */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

        <div className="relative h-full flex flex-col">
          {children}
        </div>
      </main>
    </div>
  )
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <RequireAuth>
      <RequireRole roles={MODERATOR_AND_ABOVE}>
        <DashboardContent>{children}</DashboardContent>
      </RequireRole>
    </RequireAuth>
  )
}
