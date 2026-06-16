import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  usePathname: vi.fn().mockReturnValue('/'),
}))

// Mock next/link — forward all props so title attribute is preserved
vi.mock('next/link', () => ({
  default: ({ children, href, title, className }: { children: React.ReactNode; href: string; title?: string; className?: string }) => (
    <a href={href} title={title} className={className}>{children}</a>
  ),
}))

// Mock auth provider
const mockUseAuth = vi.fn()
vi.mock('@/components/providers/auth-provider', () => ({
  useAuth: () => mockUseAuth(),
}))

// Mock auth guards to render children transparently
vi.mock('@/components/auth/require-auth', () => ({
  RequireAuth: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/components/auth/require-role', () => ({
  RequireRole: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

import { DashboardLayout } from '../dashboard-layout'

const BASE_AUTH = {
  isAuthenticated: true,
  isLoading: false,
  sessionExpired: false,
  isLoggingOut: false,
  oidcUser: { profile: { preferred_username: 'testuser' } },
  fomoUser: null,
  login: vi.fn(),
  logout: vi.fn(),
}

describe('DashboardLayout', () => {
  it('renders standard nav items for moderator', () => {
    mockUseAuth.mockReturnValue({
      ...BASE_AUTH,
      fomoUser: { id: 'u1', username: 'testuser', system_role: 'moderator' },
    })

    render(<DashboardLayout><div>content</div></DashboardLayout>)

    expect(screen.getByTitle('Pending Signals')).toBeInTheDocument()
    expect(screen.getByTitle('Published Signals')).toBeInTheDocument()
    expect(screen.getByTitle('Places')).toBeInTheDocument()
  })

  it('does NOT render admin nav item for moderator', () => {
    mockUseAuth.mockReturnValue({
      ...BASE_AUTH,
      fomoUser: { id: 'u1', username: 'testuser', system_role: 'moderator' },
    })

    render(<DashboardLayout><div>content</div></DashboardLayout>)

    expect(screen.queryByTitle('User Management')).not.toBeInTheDocument()
  })

  it('does NOT render admin nav item for manager', () => {
    mockUseAuth.mockReturnValue({
      ...BASE_AUTH,
      fomoUser: { id: 'u1', username: 'testuser', system_role: 'manager' },
    })

    render(<DashboardLayout><div>content</div></DashboardLayout>)

    expect(screen.queryByTitle('User Management')).not.toBeInTheDocument()
  })

  it('renders admin nav item for admin', () => {
    mockUseAuth.mockReturnValue({
      ...BASE_AUTH,
      fomoUser: { id: 'u1', username: 'adminuser', system_role: 'admin' },
    })

    render(<DashboardLayout><div>content</div></DashboardLayout>)

    expect(screen.getByTitle('User Management')).toBeInTheDocument()
  })

  it('admin nav item links to /admin/users', () => {
    mockUseAuth.mockReturnValue({
      ...BASE_AUTH,
      fomoUser: { id: 'u1', username: 'adminuser', system_role: 'admin' },
    })

    render(<DashboardLayout><div>content</div></DashboardLayout>)

    const adminLink = screen.getByTitle('User Management').closest('a')
    expect(adminLink).toHaveAttribute('href', '/admin/users')
  })

  it('renders children', () => {
    mockUseAuth.mockReturnValue({
      ...BASE_AUTH,
      fomoUser: { id: 'u1', username: 'mod', system_role: 'moderator' },
    })

    render(<DashboardLayout><div data-testid="content">page content</div></DashboardLayout>)

    expect(screen.getByTestId('content')).toBeInTheDocument()
  })

  it('disables the logout button while logout is in progress', () => {
    mockUseAuth.mockReturnValue({
      ...BASE_AUTH,
      isLoggingOut: true,
      fomoUser: { id: 'u1', username: 'mod', system_role: 'moderator' },
    })

    render(<DashboardLayout><div>content</div></DashboardLayout>)

    const logoutBtn = screen.getByTitle('Signing out…')
    expect(logoutBtn).toBeDisabled()
  })

  it('shows email and role in the user identity tooltip when available', () => {
    mockUseAuth.mockReturnValue({
      ...BASE_AUTH,
      fomoUser: { id: 'u1', username: 'mod', email: 'mod@example.com', system_role: 'moderator' },
    })

    render(<DashboardLayout><div>content</div></DashboardLayout>)

    expect(screen.getByTitle('mod@example.com · Moderator')).toBeInTheDocument()
  })
})
