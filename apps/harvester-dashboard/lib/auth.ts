import { UserManager, WebStorageStateStore, type User } from 'oidc-client-ts';
import type { UserSystemRole } from '@/types/api';

// ── OIDC UserManager (browser-only singleton) ─────────────────────────────────

const KEYCLOAK_URL = process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? '';
const REALM = process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? '';
const CLIENT_ID = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? '';

let _userManager: UserManager | null = null;

export function getUserManager(): UserManager {
  if (typeof window === 'undefined') {
    throw new Error('getUserManager() must only be called in the browser');
  }
  if (!_userManager) {
    _userManager = new UserManager({
      authority: `${KEYCLOAK_URL}/realms/${REALM}`,
      client_id: CLIENT_ID,
      redirect_uri: `${window.location.origin}/auth/callback`,
      post_logout_redirect_uri: `${window.location.origin}/login`,
      response_type: 'code',
      scope: 'openid email profile',
      userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    });
  }
  return _userManager;
}

/** Returns the current access token, or null if not authenticated or expired. */
export async function getAccessToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;
  try {
    const user = await getUserManager().getUser();
    if (!user || user.expired) return null;
    return user.access_token;
  } catch {
    return null;
  }
}

// ── Role hierarchy helpers ────────────────────────────────────────────────────

export const MODERATOR_AND_ABOVE: UserSystemRole[] = ['admin', 'manager', 'moderator'];
export const MANAGER_AND_ABOVE: UserSystemRole[] = ['admin', 'manager'];

export function hasModeratorAccess(role: UserSystemRole | undefined): boolean {
  if (!role) return false;
  return MODERATOR_AND_ABOVE.includes(role);
}

export function hasManagerAccess(role: UserSystemRole | undefined): boolean {
  if (!role) return false;
  return MANAGER_AND_ABOVE.includes(role);
}

export function hasAdminAccess(role: UserSystemRole | undefined): boolean {
  return role === 'admin';
}

export type { User as OidcUser };
