import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RequireAuth } from '../require-auth';

vi.mock('@/components/providers/auth-provider', () => ({
  useAuth: vi.fn(),
}));
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({ replace: vi.fn() })),
  usePathname: vi.fn(() => '/'),
}));

import { useAuth } from '@/components/providers/auth-provider';

const baseAuth = {
  oidcUser: null,
  fomoUser: null,
  isLoading: false,
  isAuthenticated: false,
  sessionExpired: false,
  isLoggingOut: false,
  login: vi.fn(),
  logout: vi.fn(),
};

describe('RequireAuth', () => {
  it('shows a loading spinner while auth state is being determined', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, isLoading: true });
    const { container } = render(<RequireAuth><div>Content</div></RequireAuth>);
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, isAuthenticated: true });
    render(<RequireAuth><div>Protected Content</div></RequireAuth>);
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('calls login() when not authenticated after loading completes', () => {
    const login = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, login });
    render(<RequireAuth><div>Protected Content</div></RequireAuth>);

    expect(login).toHaveBeenCalledOnce();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('does not call login() while still loading', () => {
    const login = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, isLoading: true, login });
    render(<RequireAuth><div>Content</div></RequireAuth>);
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });

  // ── Session expired ───────────────────────────────────────────────────────

  it('shows the session-expired screen when sessionExpired is true', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, sessionExpired: true });
    render(<RequireAuth><div>Content</div></RequireAuth>);

    expect(screen.queryByText('Content')).not.toBeInTheDocument();
    expect(screen.getByText(/session has expired/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log in again/i })).toBeInTheDocument();
  });

  it('does not auto-redirect when session is expired', () => {
    const login = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, sessionExpired: true, login });
    render(<RequireAuth><div>Content</div></RequireAuth>);

    expect(login).not.toHaveBeenCalled();
  });

  it('calls login() when "Log in again" button is clicked', () => {
    const login = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, sessionExpired: true, login });
    render(<RequireAuth><div>Content</div></RequireAuth>);

    fireEvent.click(screen.getByRole('button', { name: /log in again/i }));
    expect(login).toHaveBeenCalledOnce();
  });

  it('does not render protected content when session is expired', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, sessionExpired: true });
    render(<RequireAuth><div>Secret Content</div></RequireAuth>);
    expect(screen.queryByText('Secret Content')).not.toBeInTheDocument();
  });
});
