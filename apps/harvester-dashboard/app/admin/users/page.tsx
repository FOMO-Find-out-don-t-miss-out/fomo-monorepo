'use client'

import { useEffect, useRef, useState } from 'react'
import { DashboardLayout } from '@/components/dashboard/dashboard-layout'
import { RequireRole } from '@/components/auth/require-role'
import { useAuth } from '@/components/providers/auth-provider'
import { adminApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { UserPlus, ShieldCheck, ShieldAlert, ShieldQuestion, Users } from 'lucide-react'
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

const IDENTITY_STATUS_CONFIG: Record<string, { label: string; className: string; icon: typeof ShieldCheck }> = {
  active: { label: 'Active', className: 'badge-neon-green', icon: ShieldCheck },
  missing_in_keycloak: { label: 'Missing in Keycloak', className: 'badge-neon-red', icon: ShieldAlert },
  unknown: { label: 'Unknown', className: 'badge-neon-purple', icon: ShieldQuestion },
}

function IdentityBadge({ status }: { status: string }) {
  const cfg = IDENTITY_STATUS_CONFIG[status] ?? IDENTITY_STATUS_CONFIG.unknown
  const Icon = cfg.icon
  return (
    <Badge variant="outline" className={`${cfg.className} h-6 px-2.5 text-[10px] font-bold tracking-widest uppercase gap-1.5`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </Badge>
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

  async function handleChange(role: UserSystemRole) {
    setSaving(true)
    try {
      await onUpdate(user.id, role)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Select value={user.system_role} onValueChange={(value) => handleChange(value as UserSystemRole)} disabled={saving || isSelf}>
      <SelectTrigger
        size="sm"
        className="h-8 w-[140px] bg-card/60 input-neon text-[10px] font-bold uppercase tracking-widest"
        title={isSelf ? 'Cannot change your own role' : undefined}
      >
        <SelectValue />
      </SelectTrigger>
      <SelectContent className="bg-card border-neon-purple/20">
        {ALL_ROLES.map((role) => (
          <SelectItem key={role} value={role} className="text-[10px] font-bold uppercase tracking-widest">
            {ROLE_LABELS[role]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
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

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="card-neon bg-card border-neon-blue/20 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-foreground text-neon-glow-blue uppercase tracking-tight font-black italic">
            Invite User
          </DialogTitle>
          <DialogDescription>
            Creates a Keycloak account and a FOMO user record. The invited user must set a
            password on first login via Keycloak&#39;s &quot;Forgot password&quot; flow.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="invite-email" className="block text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">
              Email address
            </label>
            <Input
              id="invite-email"
              ref={emailRef}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="user@example.com"
              className="bg-card/60 h-10 text-sm"
            />
          </div>

          <div>
            <label htmlFor="invite-role" className="block text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">
              Role
            </label>
            <Select value={role} onValueChange={(value) => setRole(value as UserSystemRole)}>
              <SelectTrigger id="invite-role" className="w-full h-10 bg-card/60 input-neon text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-card border-neon-purple/20">
                {INVITE_ROLES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {ROLE_LABELS[r]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && (
            <p className="text-sm text-destructive rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2">
              {error}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" variant="neon-purple" disabled={loading || !email.trim()}>
              {loading ? 'Inviting…' : 'Send invite'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
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
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-10 h-10 rounded-full border-t-2 border-r-2 border-neon-blue animate-spin shadow-[0_0_15px_var(--neon-blue)]" />
        <p className="mt-4 text-[10px] font-bold uppercase tracking-[0.3em] text-neon-blue animate-pulse">Loading users...</p>
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
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-20 h-20 rounded-2xl bg-muted/10 border border-dashed border-border flex items-center justify-center mb-6">
          <Users className="w-10 h-10 text-muted-foreground/30" />
        </div>
        <p className="text-xl font-bold text-foreground/50 uppercase tracking-widest">No users found</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto scrollbar-neon">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neon-blue/10 text-left">
            <th className="px-4 py-3 font-bold text-[10px] uppercase tracking-widest text-muted-foreground">User</th>
            <th className="px-4 py-3 font-bold text-[10px] uppercase tracking-widest text-muted-foreground">Email</th>
            <th className="px-4 py-3 font-bold text-[10px] uppercase tracking-widest text-muted-foreground">Identity</th>
            <th className="px-4 py-3 font-bold text-[10px] uppercase tracking-widest text-muted-foreground">Role</th>
            <th className="px-4 py-3 font-bold text-[10px] uppercase tracking-widest text-muted-foreground">Joined</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr
              key={user.id}
              className="border-b border-border/30 hover:bg-neon-blue/5 transition-colors"
            >
              <td className="px-4 py-3 font-semibold text-foreground">
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
              <td className="px-4 py-3 text-muted-foreground text-xs">
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
        <div className="h-full flex flex-col min-h-0 bg-background/50">
          {/* Header */}
          <div className="p-6 border-b border-neon-blue/10 bg-card/40 backdrop-blur-md">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-4">
                <h1 className="text-2xl font-black text-foreground text-neon-glow-blue uppercase tracking-tighter italic">User Management</h1>
                <Badge variant="outline" className="badge-neon h-6 px-3 text-[10px] font-bold tracking-[0.2em] uppercase">
                  System Roles
                </Badge>
              </div>
              <Button variant="neon-purple" onClick={() => setDialogOpen(true)} className="shrink-0">
                <UserPlus className="w-4 h-4" />
                Invite user
              </Button>
            </div>
            <p className="text-muted-foreground text-xs mt-3 uppercase tracking-tight">
              Manage system roles for all FOMO users. Your own role cannot be changed here.
            </p>
          </div>

          <div className="flex-1 min-h-0 overflow-auto scrollbar-neon p-6">
            {successMessage && (
              <div className="mb-4 rounded-md badge-neon-green border px-4 py-3 text-sm">
                {successMessage}
              </div>
            )}

            <div className="card-neon rounded-xl border border-neon-blue/10 bg-card/40">
              {fomoUser && <UsersTable currentUserId={fomoUser.id} refreshKey={refreshKey} />}
            </div>
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
