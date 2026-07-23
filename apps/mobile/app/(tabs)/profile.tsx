import { useAuth } from '../../hooks/use-auth';
import { LogIn, LogOut, User } from 'lucide-react-native';
import React from 'react';
import {
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { FomoButton, FomoLoadingState, FomoScreen } from '../../components/ui';
import { usePerfScreenFocus } from '../../utils/performance-debug';
import { Colors, Typography, Spacing } from '../../theme';

export default function ProfileScreen() {
  usePerfScreenFocus('profile');
  const { isAuthenticated, isLoading, user, authError, login, logout } = useAuth();
  const insets = useSafeAreaInsets();

  if (isLoading) {
    return (
      <FomoScreen>
        <FomoLoadingState />
      </FomoScreen>
    );
  }

  // Auth gate in _layout.tsx should redirect unauthenticated users to /login.
  // This fallback handles any edge case where the tab is reached without auth.
  if (!isAuthenticated) {
    return (
      <FomoScreen style={[styles.center, { paddingTop: insets.top }]}>
        <User size={48} color={Colors.textDisabled} strokeWidth={1} />
        <Text style={styles.heading}>Sign in to FOMO</Text>
        {authError ? <Text style={styles.error}>{authError}</Text> : null}
        <FomoButton
          label="Log In"
          icon={<LogIn size={18} color="#fff" strokeWidth={1.5} />}
          onPress={() => login()}
          style={styles.loginBtnWidth}
        />
      </FomoScreen>
    );
  }

  return (
    <FomoScreen style={[styles.container, { paddingTop: insets.top + 24 }]}>
      <View style={styles.avatarRing}>
        <User size={40} color={Colors.purple} strokeWidth={1.5} />
      </View>

      <Text style={styles.username}>{user?.username ?? '—'}</Text>
      {user?.email ? <Text style={styles.email}>{user.email}</Text> : null}

      <View style={styles.divider} />

      <InfoRow label="Role" value={user?.system_role ?? '—'} />
      <InfoRow label="Member since" value={user?.created_at ? formatDate(user.created_at) : '—'} />

      {authError ? <Text style={styles.error}>{authError}</Text> : null}

      <FomoButton
        label="Log Out"
        variant="ghost"
        icon={<LogOut size={16} color={Colors.textSecondary} strokeWidth={1.5} />}
        onPress={logout}
        style={styles.logoutBtnMargin}
      />
    </FomoScreen>
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
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing['2xl'],
    gap: Spacing.md,
  },
  container: {
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
  },
  heading: {
    color: Colors.textPrimary,
    fontSize: Typography.size['2xl'],
    fontFamily: Typography.font.bold,
    marginTop: Spacing.sm,
  },
  error: {
    color: Colors.error,
    fontSize: Typography.size.base,
    fontFamily: Typography.font.regular,
    textAlign: 'center',
    marginBottom: Spacing.xs,
  },
  loginBtnWidth: {
    width: '100%',
    marginTop: Spacing.sm,
  },
  avatarRing: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 1.5,
    borderColor: `${Colors.purple}66`,
    backgroundColor: `${Colors.purple}14`,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
  },
  username: {
    color: Colors.textPrimary,
    fontSize: Typography.size['2xl'],
    fontFamily: Typography.font.bold,
    letterSpacing: 0.3,
  },
  email: {
    color: Colors.textSecondary,
    fontSize: Typography.size.base,
    fontFamily: Typography.font.regular,
    marginTop: 2,
  },
  divider: {
    width: '100%',
    height: 1,
    backgroundColor: Colors.borderSubtle,
    marginVertical: Spacing.xl,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  infoLabel: {
    color: 'rgba(255,255,255,0.4)',
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.base,
  },
  infoValue: {
    color: 'rgba(255,255,255,0.85)',
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.base,
    textTransform: 'capitalize',
  },
  logoutBtnMargin: {
    marginTop: Spacing['2xl'],
  },
});
