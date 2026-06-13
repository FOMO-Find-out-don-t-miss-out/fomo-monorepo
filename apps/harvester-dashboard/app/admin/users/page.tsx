'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout } from '@/components/dashboard/dashboard-layout'
import { RequireRole } from '@/components/auth/require-role'
import { useAuth } from '@/components/providers/auth-provider'
import { adminApi } from '@/lib/api'
import type { UserAdminResponse, UserSystemRole } from '@/types/api'

const ALL_ROLES: UserSystemRole[] = ['admin', 'manager', 'moderator', 'user', 'service']

const ROLE_LABELS: Record<UserSystemRole, string> = {
  admin: 'Admin',
  manager: 'Manager',
  moderator: 'Moderator',
  user: 'User',
  service: 'Service',
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

function UsersTable({ currentUserId }: { currentUserId: string }) {
  const [users, setUsers] = useState<UserAdminResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    adminApi.getUsers()
      .then(setUsers)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

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
            <th className="px-4 py-3 font-medium">External ID</th>
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
              <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                {user.external_id}
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

export default function AdminUsersPage() {
  const { fomoUser } = useAuth()

  return (
    <DashboardLayout>
      <RequireRole roles={['admin']}>
        <div className="p-6 space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-foreground">User Management</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Manage system roles for all FOMO users. Your own role cannot be changed here.
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card">
            {fomoUser && <UsersTable currentUserId={fomoUser.id} />}
          </div>
        </div>
      </RequireRole>
    </DashboardLayout>
  )
}
