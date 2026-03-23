'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Calendar,
  MapPin,
  LayoutDashboard,
  Settings,
  Flame,
  CheckCheck
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/', label: 'Pending', icon: Calendar },
  { href: '/published', label: 'Published', icon: CheckCheck },
  { href: '/venues', label: 'Venues', icon: MapPin },
]

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname()

  return (
    <div className="flex h-screen bg-background">
      {/* Fixed Left Navigation */}
      <aside className="w-16 flex-shrink-0 border-r border-border bg-sidebar flex flex-col items-center py-4">
        {/* Logo */}
        <div className="mb-8">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
            <Flame className="w-5 h-5 text-primary-foreground" />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'w-10 h-10 rounded-lg flex items-center justify-center transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                )}
                title={item.label}
              >
                <item.icon className="w-5 h-5" />
              </Link>
            )
          })}
        </nav>

        {/* Bottom actions */}
        <div className="mt-auto flex flex-col gap-2">
          <button
            className="w-10 h-10 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  )
}
