'use client'

import { useEffect, useRef, useState } from 'react'
import { DashboardLayout } from '@/components/dashboard/dashboard-layout'
import { RequireRole } from '@/components/auth/require-role'
import { useAuth } from '@/components/providers/auth-provider'
import { adminApi } from '@/lib/api'
import type { UserAdminResponse, UserSystemRole, InviteUserRequest } from '@/types/api'

const ALL_ROLES: UserSystemRole[] = ['admin', 'manager', 'moderator', 'user', 'service']
const INVITE_ROLES: UserSystemRole[] = ['admin', 'manager', 'moderator', 'user']

const ROLE_LABELS: Record<UserSystemRole, string> = {
  admin: 'Admin',
  manager: 'Manager',
  moderator: 'Moderator',
  user: 'User',
  service: 'Service',
}

const IDENTITY_STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  active: { label: 'Active', className: 'bg-green-500/10 text-green-600 dark:text-green-400' },
  missing_in_keycloak: { label: 'Missing in Keycloak', className: 'bg-red-500/10 text-red-600 dark:text-red-400' },
  unknown: { label: 'Unknown', className: 'bg-muted text-muted-foreground' },
}

function IdentityBadge({ status }: { status: string }) {
  const cfg = IDENTITY_STATUS_CONFIG[status] ?? IDENTITY_STATUS_CONFIG.unknown
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cfg.className}`}>
      {cfg.label}
    </span>
  )
}

function RoleSelect({
  user,
  currentUserId,
  onUpdate,
}: {
  user: UserAdminResponse
  currentUserId: string
  onUpdate: (userId: string, role: UserSystemRole) => Promise<void>
}) {
  const [saving, setSaving] = useState(false)
  const isSelf = user.id === currentUserId

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const role = e.target.value as UserSystemRole
    setSaving(true)
    try {
      await onUpdate(user.id, role)
    } finally {
      setSaving(false)
    }
  }

  return (
    <select
      value={user.system_role}
      onChange={handleChange}
      disabled={saving || isSelf}
      title={isSelf ? 'Cannot change your own role' : undefined}
      className="bg-background border border-border rounded px-2 py-1 text-sm text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {ALL_ROLES.map((role) => (
        <option key={role} value={role}>
          {ROLE_LABELS[role]}
        </option>
      ))}
    </select>
  )
}

// ── Invite dialog ─────────────────────────────────────────────────────────────

interface InviteDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: (message: string) => void
}

function InviteDialog({ open, onClose, onSuccess }: InviteDialogProps) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<UserSystemRole>('user')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const emailRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setEmail('')
      setRole('user')
      setError(null)
      setTimeout(() => emailRef.current?.focus(), 50)
    }
  }, [open])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const body: InviteUserRequest = { email: email.trim().toLowerCase(), system_role: role }
      const result = await adminApi.inviteUser(body)
      const kc = result.keycloak_created ? ' (Keycloak account created)' : ' (linked to existing Keycloak identity)'
      onSuccess(`Invited ${result.email} as ${ROLE_LABELS[result.system_role]}${kc}.`)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to invite user')
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-foreground mb-1">Invite user</h2>
        <p className="text-sm text-muted-foreground mb-5">
          Creates a Keycloak account and a FOMO user record. The invited user must set a
          password on first login via Keycloak&#39;s &quot;Forgot password&quot; flow.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="invite-email" className="block text-sm font-medium text-foreground mb-1">
              Email address
            </label>
            <input
              id="invite-email"
              ref={emailRef}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="user@example.com"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label htmlFor="invite-role" className="block text-sm font-medium text-foreground mb-1">
              Role
            </label>
            <select
              id="invite-role"
              value={role}
              onChange={(e) => setRole(e.target.value as UserSystemRole)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {INVITE_ROLES.map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABELS[r]}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-md px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Inviting…' : 'Send invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Users table ───────────────────────────────────────────────────────────────

interface UsersTableProps {
  currentUserId: string
  refreshKey: number
}

function UsersTable({ currentUserId, refreshKey }: UsersTableProps) {
  const [users, setUsers] = useState<UserAdminResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    adminApi.getUsers()
      .then(setUsers)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  async function handleRoleUpdate(userId: string, role: UserSystemRole) {
    try {
      const updated = await adminApi.updateUserRole(userId, { system_role: role })
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
        Loading users…
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20 text-destructive text-sm">
        {error}
      </div>
    )
  }

  if (users.length === 0) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
        No users found.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-muted-foreground text-left">
            <th className="px-4 py-3 font-medium">User</th>
            <th className="px-4 py-3 font-medium">Email</th>
            <th className="px-4 py-3 font-medium">Identity</th>
            <th className="px-4 py-3 font-medium">Role</th>
            <th className="px-4 py-3 font-medium">Joined</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr
              key={user.id}
              className="border-b border-border/50 hover:bg-muted/10 transition-colors"
            >
              <td className="px-4 py-3 font-medium text-foreground">
                {user.username ?? <span className="text-muted-foreground italic">—</span>}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {user.email ?? '—'}
              </td>
              <td className="px-4 py-3">
                <IdentityBadge status={user.identity_status} />
              </td>
              <td className="px-4 py-3">
                <RoleSelect
                  user={user}
                  currentUserId={currentUserId}
                  onUpdate={handleRoleUpdate}
                />
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {new Date(user.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminUsersPage() {
  const { fomoUser } = useAuth()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  function handleInviteSuccess(message: string) {
    setSuccessMessage(message)
    setRefreshKey((k) => k + 1)
    setTimeout(() => setSuccessMessage(null), 6000)
  }

  return (
    <DashboardLayout>
      <RequireRole roles={['admin']}>
        <div className="p-6 space-y-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-foreground">User Management</h1>
              <p className="text-muted-foreground text-sm mt-1">
                Manage system roles for all FOMO users. Your own role cannot be changed here.
              </p>
            </div>
            <button
              onClick={() => setDialogOpen(true)}
              className="shrink-0 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              + Invite user
            </button>
          </div>

          {successMessage && (
            <div className="rounded-md bg-green-500/10 border border-green-500/20 px-4 py-3 text-sm text-green-700 dark:text-green-400">
              {successMessage}
            </div>
          )}

          <div className="rounded-xl border border-border bg-card">
            {fomoUser && <UsersTable currentUserId={fomoUser.id} refreshKey={refreshKey} />}
          </div>
        </div>

        <InviteDialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          onSuccess={handleInviteSuccess}
        />
      </RequireRole>
    </DashboardLayout>
  )
}
