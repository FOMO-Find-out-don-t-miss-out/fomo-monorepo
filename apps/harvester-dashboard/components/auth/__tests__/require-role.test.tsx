import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RequireRole } from '../require-role';
import type { UserMeResponse } from '@/types/api';

vi.mock('@/components/providers/auth-provider', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '@/components/providers/auth-provider';

function makeUser(role: UserMeResponse['system_role']): UserMeResponse {
  return {
    id: 'test-id',
    external_id: 'sub',
    email: null,
    phone_number: null,
    phone_verified: false,
    system_role: role,
    username: 'tester',
    avatar_url: null,
    created_at: '',
    updated_at: '',
  };
}

const baseAuth = {
  oidcUser: null,
  isLoading: false,
  isAuthenticated: true,
  login: vi.fn(),
  logout: vi.fn(),
};

describe('RequireRole', () => {
  it('renders children when user has a required role (moderator)', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, fomoUser: makeUser('moderator') });
    render(
      <RequireRole roles={['admin', 'manager', 'moderator']}>
        <div>Protected Content</div>
      </RequireRole>
    );
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('renders children when user has an elevated required role (admin)', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, fomoUser: makeUser('admin') });
    render(
      <RequireRole roles={['admin', 'manager', 'moderator']}>
        <div>Admin Content</div>
      </RequireRole>
    );
    expect(screen.getByText('Admin Content')).toBeInTheDocument();
  });

  it('renders the default forbidden UI when role is insufficient (user)', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, fomoUser: makeUser('user') });
    render(
      <RequireRole roles={['admin', 'manager', 'moderator']}>
        <div>Protected Content</div>
      </RequireRole>
    );
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(screen.getByText(/don't have permission/i)).toBeInTheDocument();
  });

  it('renders the default forbidden UI when role is isolated (service)', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, fomoUser: makeUser('service') });
    render(
      <RequireRole roles={['admin', 'manager', 'moderator']}>
        <div>Protected Content</div>
      </RequireRole>
    );
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders a custom fallback when role is insufficient', () => {
    vi.mocked(useAuth).mockReturnValue({ ...baseAuth, fomoUser: makeUser('user') });
    render(
      <RequireRole roles={['admin']} fallback={<div>Custom Forbidden</div>}>
        <div>Protected Content</div>
      </RequireRole>
    );
    expect(screen.getByText('Custom Forbidden')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders a loading spinner when authenticated but fomoUser not yet loaded', () => {
    vi.mocked(useAuth).mockReturnValue({
      ...baseAuth,
      fomoUser: null,
      isAuthenticated: true,
    });
    render(
      <RequireRole roles={['moderator']}>
        <div>Protected Content</div>
      </RequireRole>
    );
    // Loading state — neither content nor forbidden should be visible
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(screen.queryByText(/don't have permission/i)).not.toBeInTheDocument();
  });

  it('renders forbidden when not authenticated and no fomoUser', () => {
    vi.mocked(useAuth).mockReturnValue({
      ...baseAuth,
      fomoUser: null,
      isAuthenticated: false,
    });
    render(
      <RequireRole roles={['moderator']}>
        <div>Protected Content</div>
      </RequireRole>
    );
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(screen.getByText(/don't have permission/i)).toBeInTheDocument();
  });
});
