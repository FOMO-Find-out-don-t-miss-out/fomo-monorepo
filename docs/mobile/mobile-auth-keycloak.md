# Mobile Keycloak Authentication

FOMO-170 — Authorization Code + PKCE via Expo AuthSession.

## Realm assignment

| Client | Realm | Notes |
|---|---|---|
| Mobile app (`fomo-mobile`) | `fomo-users` | End-user realm |
| Dashboard (`fomo-dashboard`) | `fomo-admin` | Internal staff realm |

**Mobile must never authenticate against `fomo-admin`.** That realm is for internal dashboard users only.

## Architecture

```
User taps Continue with Google
  └─► expo-auth-session builds authorization URL (PKCE S256)
        └─► kc_idp_hint=google appended to URL
              └─► Keycloak fomo-users broker flow (Chrome Custom Tab)
                    └─► Google OAuth consent
                          └─► redirect fomo://auth/callback?code=…
                                └─► code exchange (PKCE verifier)
                                      └─► Keycloak-issued JWT stored in SecureStore
                                            └─► GET /api/v1/users/me (Bearer token)
                                                  └─► app enters Discover tab
```

The backend **always** validates Keycloak-issued tokens from the `fomo-users` realm — never raw Google tokens. Keycloak acts as the identity broker.

## IdP hint — how it works

When `login({ idpHint: 'google' })` is called, the auth provider:

1. Calls `request.buildUrlAsync(discovery)` to get the full authorization URL (includes `code_challenge`, `state`, `nonce`).
2. Appends `&kc_idp_hint=google` to that URL.
3. Opens `WebBrowser.openAuthSessionAsync(hintedUrl, redirectUri)` directly.
4. Parses `code` from the callback URL.
5. Exchanges the code using the same PKCE `code_verifier` — identical to the standard flow.

Keycloak receives `kc_idp_hint` and skips its own login page, redirecting immediately to the Google OAuth consent screen. No username/password form is shown.

## App access gate

Mobile is a registered-user experience. All content is gated behind login:

- **Unauthenticated** → login/welcome screen (`/login`); no tabs visible
- **Authenticated** → full app; tabs unlocked

The gate is implemented in `app/_layout.tsx` via the `AuthGate` component. It holds a loading spinner while auth state is being determined (including during pending redirects) to prevent Mapbox and other tab-mounted components from instantiating before the screen transition completes.

## Login screen UI

- **Primary**: white `Continue with Google` button → `login({ idpHint: 'google' })`
- **Secondary**: low-contrast `Use email instead` text link → `login()` (opens Keycloak form; useful for dev/testing)

Apple login can be added later with `login({ idpHint: 'apple' })` once the Apple IdP is configured in `fomo-users` with alias `apple`.

## Required environment variables

Add these to `apps/mobile/.env` (see `.env.example`):

| Variable | Value | Notes |
|---|---|---|
| `EXPO_PUBLIC_AUTH_URL` | `https://auth.staging.fomo-lab.org` | Keycloak base URL |
| `EXPO_PUBLIC_KEYCLOAK_REALM` | `fomo-users` | End-user realm — NOT `fomo-admin` |
| `EXPO_PUBLIC_KEYCLOAK_CLIENT_ID` | `fomo-mobile` | Public client (no secret) |
| `EXPO_PUBLIC_AUTH_REDIRECT_SCHEME` | `fomo` | Must match `scheme` in `app.json` |

## Keycloak client settings (`fomo-users` realm)

The `fomo-mobile` client must be configured with:

| Setting | Value |
|---|---|
| Client type | OpenID Connect |
| Access type | Public |
| Standard flow | Enabled |
| Direct access grants | Disabled |
| Valid redirect URIs | `fomo://auth/callback` (or `fomo://*`) |
| Web origins | `+` |
| PKCE method | S256 |

The exact URI the app sends is `fomo://auth/callback` (logged on startup as `[auth] redirect URI: fomo://auth/callback`).

## Google Identity Provider setup (`fomo-users` realm)

Configure a Google Identity Provider in the `fomo-users` realm:

| Setting | Value |
|---|---|
| Provider type | Google |
| Alias | `google` — **must match exactly** |
| Enabled | Yes |
| Client ID | Google OAuth client ID |
| Client Secret | Google OAuth client secret |
| Default Scopes | `openid email profile` |
| First Login Flow | `first broker login` (default) |
| Sync Mode | `IMPORT` |

The Google OAuth client (in Google Cloud Console) must have the Keycloak broker callback as an authorised redirect URI:
```
https://auth.staging.fomo-lab.org/realms/fomo-users/broker/google/endpoint
```

The `first broker login` flow creates a FOMO user from the Google account on first authentication and links subsequent logins to the same user automatically.

### Verifying the IdP hint works

If tapping `Continue with Google` still shows the Keycloak username/password page:

1. Check dev logs: `[auth] kc_idp_hint` should appear before the browser opens (if you add a log — not included by default).
2. Confirm the Google IdP alias in Keycloak is exactly `google` (case-sensitive).
3. Confirm the Google IdP is **Enabled** in the `fomo-users` realm → Identity Providers.
4. Try opening the hinted URL directly in a browser to see the Keycloak error.

## Issuer and discovery

- **Issuer**: `https://auth.staging.fomo-lab.org/realms/fomo-users`
- **OIDC discovery**: `https://auth.staging.fomo-lab.org/realms/fomo-users/.well-known/openid-configuration`

## Redirect URI

`makeRedirectUri({ scheme: 'fomo', path: 'auth/callback' })` produces `fomo://auth/callback`.

`app/auth/callback.tsx` exists as a safety net so Expo Router never 404s on that path.

## Backend JWT compatibility

The API validates the `iss` claim against `AUTH_OIDC_ISSUER` plus any issuers in `AUTH_OIDC_EXTRA_ISSUERS`. Tokens are always Keycloak-issued — not Google-issued.

**Required staging backend config:**

```env
AUTH_OIDC_ISSUER=https://auth.staging.fomo-lab.org/realms/fomo-admin
AUTH_OIDC_EXTRA_ISSUERS=https://auth.staging.fomo-lab.org/realms/fomo-users
AUTH_OIDC_ALLOWED_AZP=fomo-dashboard,fomo-mobile
```

The JWKS URL is derived automatically as `{issuer}/protocol/openid-connect/certs`.

## Key files

| File | Purpose |
|---|---|
| `apps/mobile/utils/auth-client.ts` | ISSUER/CLIENT_ID constants, SecureStore helpers, token refresh |
| `apps/mobile/providers/auth-provider.tsx` | React context — PKCE flow, IdP hint, session restore |
| `apps/mobile/hooks/use-auth.ts` | Re-exports `useAuth`, `AuthContextValue`, `LoginOptions` |
| `apps/mobile/app/login.tsx` | Login/welcome screen — Google button + email fallback |
| `apps/mobile/app/_layout.tsx` | `AuthGate` — holds spinner during loading and pending redirects |
| `apps/mobile/app/auth/callback.tsx` | Expo Router safety net for `fomo://auth/callback` deep link |
| `apps/mobile/app/(tabs)/profile.tsx` | Profile tab — shows user info and logout |
| `apps/api/app/core/security/jwt_validator.py` | Multi-issuer JWT validation |
| `apps/api/app/core/security/jwks.py` | Per-issuer JWKS client cache |

## Token storage

Tokens are stored in `expo-secure-store` (Keystore on Android, Keychain on iOS):

| Key | Content |
|---|---|
| `fomo_access_token` | Keycloak access token (JWT) |
| `fomo_refresh_token` | Keycloak refresh token |

Tokens are **never** logged or passed through UI component props.

## Session lifecycle

1. **App start** — `AuthGate` shows a loading spinner while `AuthProvider` restores the session.
   - Tries refresh token first; falls back to access token; clears and redirects to `/login` on failure.
2. **Login** — Chrome Custom Tab opens; Keycloak brokers to Google (or shows form for email path).
   - Code exchange returns tokens; stored securely; `AuthGate` redirects to `/`.
3. **Logout** — clears all tokens; `AuthGate` redirects to `/login`.
4. **Session expiry** — failed token refresh clears session and redirects to login gate.

## Testing Google login end-to-end

1. Clear app data: `adb shell pm clear com.fomo.mobile`
2. Open the app — login/welcome gate should appear.
3. Tap **Continue with Google** — Chrome Custom Tab should open directly to the Google account chooser (not the Keycloak form).
4. Select a Google account and grant consent.
5. App returns to Discover tab (authenticated).
6. Open Profile tab — shows username and email from `/users/me`.
7. Tap **Log Out** — returns to login gate.
8. Restart the app — session restores silently if tokens are still valid.

## Old-realm token cleanup

If a device previously stored tokens from the `fomo-admin` realm, the refresh exchange will fail (wrong issuer endpoint). `AuthProvider` detects this and calls `clearTokens()`, returning the user to the login screen. No crash occurs.

Manual clear: `adb shell pm clear com.fomo.mobile` or uninstall/reinstall.

## Adding Apple login (future)

Once an Apple IdP with alias `apple` is configured in `fomo-users`:

1. Add `login({ idpHint: 'apple' })` button to `login.tsx`.
2. No auth-provider changes needed — the `idpHint` param handles it.
3. iOS only: ensure the Apple Sign In entitlement is added to `app.json`.

## Known limitations / follow-ups

- **Logout does not invalidate the Keycloak browser session** — a subsequent login may re-authenticate silently via Google SSO. Call the `end_session` endpoint to force re-login.
- **iOS not tested** — redirect URI and flow should work; requires the same Keycloak config.
- **Saved / Interested / Going** — deferred (FOMO-170 scope).
- **Profile editing** — deferred.
