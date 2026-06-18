import { useAuth } from '../../hooks/use-auth';
import { LogIn, LogOut, User } from 'lucide-react-native';
import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function ProfileScreen() {
  const { isAuthenticated, isLoading, user, authError, login, logout } = useAuth();
  const insets = useSafeAreaInsets();

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#A855F7" size="large" />
      </View>
    );
  }

  // Auth gate in _layout.tsx should redirect unauthenticated users to /login.
  // This fallback handles any edge case where the tab is reached without auth.
  if (!isAuthenticated) {
    return (
      <View style={[styles.center, { paddingTop: insets.top }]}>
        <User size={48} color="rgba(255,255,255,0.2)" strokeWidth={1} />
        <Text style={styles.heading}>Sign in to FOMO</Text>
        {authError ? <Text style={styles.error}>{authError}</Text> : null}
        <Pressable style={styles.loginBtn} onPress={login}>
          <LogIn size={18} color="#fff" strokeWidth={1.5} />
          <Text style={styles.loginBtnText}>Log In</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top + 24 }]}>
      <View style={styles.avatarRing}>
        <User size={40} color="#A855F7" strokeWidth={1.5} />
      </View>

      <Text style={styles.username}>{user?.username ?? '—'}</Text>
      {user?.email ? <Text style={styles.email}>{user.email}</Text> : null}

      <View style={styles.divider} />

      <InfoRow label="Role" value={user?.system_role ?? '—'} />
      <InfoRow label="Member since" value={user?.created_at ? formatDate(user.created_at) : '—'} />

      {authError ? <Text style={styles.error}>{authError}</Text> : null}

      <Pressable style={styles.logoutBtn} onPress={logout}>
        <LogOut size={16} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
        <Text style={styles.logoutBtnText}>Log Out</Text>
      </Pressable>
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 12,
  },
  container: {
    flex: 1,
    backgroundColor: '#0B0B0F',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  heading: {
    color: '#fff',
    fontSize: 22,
    fontFamily: 'Inter_700Bold',
    marginTop: 8,
  },
  sub: {
    color: 'rgba(255,255,255,0.45)',
    fontSize: 14,
    fontFamily: 'Inter_400Regular',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 8,
  },
  error: {
    color: '#F87171',
    fontSize: 13,
    fontFamily: 'Inter_400Regular',
    textAlign: 'center',
    marginBottom: 4,
  },
  loginBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#A855F7',
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 12,
    marginTop: 8,
  },
  loginBtnText: {
    color: '#fff',
    fontFamily: 'Inter_600SemiBold',
    fontSize: 15,
  },
  avatarRing: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 1.5,
    borderColor: 'rgba(168,85,247,0.4)',
    backgroundColor: 'rgba(168,85,247,0.08)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  username: {
    color: '#fff',
    fontSize: 20,
    fontFamily: 'Inter_700Bold',
    letterSpacing: 0.3,
  },
  email: {
    color: 'rgba(255,255,255,0.45)',
    fontSize: 13,
    fontFamily: 'Inter_400Regular',
    marginTop: 2,
  },
  divider: {
    width: '100%',
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.08)',
    marginVertical: 24,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  infoLabel: {
    color: 'rgba(255,255,255,0.4)',
    fontFamily: 'Inter_500Medium',
    fontSize: 13,
  },
  infoValue: {
    color: 'rgba(255,255,255,0.85)',
    fontFamily: 'Inter_500Medium',
    fontSize: 13,
    textTransform: 'capitalize',
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 32,
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  logoutBtnText: {
    color: 'rgba(255,255,255,0.6)',
    fontFamily: 'Inter_500Medium',
    fontSize: 14,
  },
});
