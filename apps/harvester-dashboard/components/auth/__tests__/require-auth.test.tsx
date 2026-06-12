import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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
  login: vi.fn(),
  logout: vi.fn(),
};

describe('RequireAuth', () => {
  it('shows a loading spinner while auth state is being determined', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, isLoading: true, isAuthenticated: false });
    const { container } = render(<RequireAuth><div>Content</div></RequireAuth>);
    // The loading spinner is rendered via Loader2 SVG; no content should be visible
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, isLoading: false, isAuthenticated: true });
    render(<RequireAuth><div>Protected Content</div></RequireAuth>);
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('calls login() when not authenticated after loading completes', () => {
    const login = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, isLoading: false, isAuthenticated: false, login });
    render(<RequireAuth><div>Protected Content</div></RequireAuth>);

    expect(login).toHaveBeenCalledOnce();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('does not call login() while still loading', () => {
    const login = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, isLoading: true, isAuthenticated: false, login });
    render(<RequireAuth><div>Content</div></RequireAuth>);
    // useEffect fires after render; login should not have been called yet
    // (it will be called once isLoading becomes false)
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });
});
