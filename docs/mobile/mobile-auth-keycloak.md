# Mobile Keycloak Authentication

FOMO-170 — Authorization Code + PKCE via Expo AuthSession.

## Architecture

```
User taps Login
  └─► expo-auth-session (PKCE)
        └─► Keycloak browser flow (Chrome Custom Tab / ASWebAuthSession)
              └─► redirected back to fomo:// 
                    └─► code exchange (expo-auth-session)
                          └─► tokens stored in expo-secure-store
                                └─► GET /api/v1/users/me (Bearer token)
                                      └─► Profile screen shows user info
```

## Required environment variables

Add these to `apps/mobile/.env` (see `.env.example`):

| Variable | Value | Notes |
|---|---|---|
| `EXPO_PUBLIC_AUTH_URL` | `https://auth.staging.fomo-lab.org` | Keycloak base URL |
| `EXPO_PUBLIC_KEYCLOAK_REALM` | `fomo-admin` | Keycloak realm |
| `EXPO_PUBLIC_KEYCLOAK_CLIENT_ID` | `fomo-mobile` | Public client (no secret) |
| `EXPO_PUBLIC_AUTH_REDIRECT_SCHEME` | `fomo` | Must match `scheme` in `app.json` |

## Keycloak client settings

The `fomo-mobile` client in the `fomo-admin` realm must be configured with:

| Setting | Value |
|---|---|
| Client type | OpenID Connect |
| Access type | Public |
| Standard flow | Enabled |
| Direct access grants | Disabled |
| Valid redirect URIs | `fomo://*` |
| Web origins | `+` (use Valid Redirect URIs) |
| PKCE method | S256 |

**Valid redirect URIs**: `fomo://*` covers both `fomo://` (native dev build) and any future path variants. If you prefer an exact match, use `fomo://`.

## Issuer and discovery

- **Issuer**: `https://auth.staging.fomo-lab.org/realms/fomo-admin`
- **OIDC discovery URL**: `https://auth.staging.fomo-lab.org/realms/fomo-admin/.well-known/openid-configuration`

## Redirect URI

Expo AuthSession generates the redirect URI from the `scheme` in `app.json`:

```
fomo://
```

This is sent as the `redirect_uri` parameter during the auth code request and must be registered in Keycloak.

## Key files

| File | Purpose |
|---|---|
| `apps/mobile/utils/auth-client.ts` | ISSUER/CLIENT_ID constants, SecureStore helpers, token refresh |
| `apps/mobile/providers/auth-provider.tsx` | React context — PKCE flow, session restore, login/logout |
| `apps/mobile/hooks/use-auth.ts` | Re-exports `useAuth` and `AuthContextValue` |
| `apps/mobile/app/_layout.tsx` | Wraps app in `<AuthProvider>` |
| `apps/mobile/app/(tabs)/profile.tsx` | Profile tab — shows login or user info |

## Token storage

Tokens are stored using `expo-secure-store` (Keystore on Android, Keychain on iOS):

| Key | Content |
|---|---|
| `fomo_access_token` | Keycloak access token (JWT) |
| `fomo_refresh_token` | Keycloak refresh token |

Tokens are **never** logged or passed through UI component props.

## Session lifecycle

1. **App start** — checks SecureStore for a refresh token, attempts silent refresh. Falls back to access-token-only if no refresh token. Clears session if all tokens are invalid/expired.
2. **Login** — opens Keycloak in a Chrome Custom Tab (Android) or ASWebAuthSession (iOS). On return, exchanges the auth code for tokens and stores them securely.
3. **Logout** — clears all tokens from SecureStore and resets local state. Keycloak session is not explicitly invalidated (browser session may persist).
4. **Token expiry** — calling `refreshSession()` from any screen or hook triggers a silent token refresh. Failed refresh clears the session.

## How `/api/v1/users/me` is called

After a successful code exchange, the auth provider calls:

```
GET https://api.staging.fomo-lab.org/api/v1/users/me
Authorization: Bearer <access_token>
```

The backend (`apps/api/app/api/v1/users.py`) validates the JWT against Keycloak's JWKS endpoint and creates the FOMO user + default profile on first access (idempotent). The `UserMeResponse` schema is returned and stored in auth context.

## Testing login/logout

1. Build and install the Android dev APK.
2. Open the Profile tab — should show "Sign in to FOMO".
3. Tap **Log In** — Chrome Custom Tab opens Keycloak.
4. Enter Keycloak credentials → submit.
5. App opens with `fomo://` redirect and returns to Profile tab.
6. Profile shows `username`, `email` (if set), and `system_role` from `/api/v1/users/me`.
7. Tap **Log Out** — Profile returns to the logged-out state.
8. Restart the app — if tokens are still valid, session is restored silently (no login prompt).

## Public discovery (no login required)

The Discover, Search, Map, and Event Detail screens remain fully public. No auth token is sent for those requests. `AuthProvider` is loaded at the root level but only applies tokens when explicitly used.

## Known limitations / follow-ups

- **Logout does not invalidate the Keycloak browser session**: a subsequent login tap may re-authenticate silently without showing a credentials form. To force re-login, the end_session endpoint must be called — this can be added if needed.
- **`offline_access` scope**: requested during login to obtain a long-lived refresh token. If the `fomo-mobile` client does not grant this scope, the refresh token will still be issued but with a shorter TTL (configured in Keycloak's realm settings).
- **iOS not tested**: only Android dev build tested. iOS requires the same Keycloak redirect URI (`fomo://`) and the scheme in `app.json` already covers it.
- **Saved / Interested / Going**: not implemented (FOMO-170 scope). Auth layer is in place for these features.
