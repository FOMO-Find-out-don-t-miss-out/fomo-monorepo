import { useAuth } from '../hooks/use-auth';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Typography, Spacing, Radii } from '../theme';

export default function LoginScreen() {
  const { isLoading, login, authError } = useAuth();
  const insets = useSafeAreaInsets();
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const handleLogin = async (idpHint?: string) => {
    setIsLoggingIn(true);
    try {
      await login(idpHint ? { idpHint } : undefined);
    } finally {
      setIsLoggingIn(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator color={Colors.purple} size="large" />
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top, paddingBottom: insets.bottom + 24 }]}>
      <View style={styles.logoArea}>
        <View style={styles.logoRing}>
          <Text style={styles.logoText}>F</Text>
        </View>
        <Text style={styles.appName}>FOMO</Text>
        <Text style={styles.tagline}>{"Find out, don't miss out."}</Text>
      </View>

      <View style={styles.footer}>
        {authError ? <Text style={styles.error}>{authError}</Text> : null}

        {isLoggingIn ? (
          <View style={styles.loggingIn}>
            <ActivityIndicator color={Colors.purple} size="small" />
            <Text style={styles.loggingInText}>Opening login…</Text>
          </View>
        ) : (
          <>
            <Pressable
              style={styles.googleBtn}
              onPress={() => handleLogin('google')}
              accessibilityRole="button"
              accessibilityLabel="Continue with Google"
            >
              <View style={styles.googleIconBox}>
                <Text style={styles.googleIconLetter}>G</Text>
              </View>
              <Text style={styles.googleBtnText}>Continue with Google</Text>
            </Pressable>

            <Pressable
              onPress={() => handleLogin()}
              accessibilityRole="button"
              accessibilityLabel="Use email instead"
            >
              <Text style={styles.emailLink}>Use email instead</Text>
            </Pressable>
          </>
        )}

        <Text style={styles.hint}>
          A FOMO account is required to access the app.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing['2xl'],
  },
  logoArea: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.md,
  },
  logoRing: {
    width: 96,
    height: 96,
    borderRadius: 48,
    borderWidth: 2,
    borderColor: `${Colors.purple}99`,
    backgroundColor: `${Colors.purple}1A`,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.sm,
  },
  logoText: {
    color: Colors.purple,
    fontSize: 48,
    fontFamily: Typography.font.extraBold,
    lineHeight: 56,
  },
  appName: {
    color: Colors.textPrimary,
    fontSize: Typography.size.hero,
    fontFamily: Typography.font.extraBold,
    letterSpacing: 6,
  },
  tagline: {
    color: Colors.textMuted,
    fontSize: Typography.size.md,
    fontFamily: Typography.font.regular,
    letterSpacing: 0.3,
  },
  footer: {
    width: '100%',
    alignItems: 'center',
    gap: 14,
    paddingBottom: Spacing.sm,
  },
  error: {
    color: Colors.error,
    fontSize: Typography.size.base,
    fontFamily: Typography.font.regular,
    textAlign: 'center',
  },
  // Google button — white background follows Google brand guidelines
  googleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    backgroundColor: '#fff',
    paddingHorizontal: Spacing.xl,
    paddingVertical: 14,
    borderRadius: Radii.lg,
    width: '100%',
    justifyContent: 'center',
  },
  googleIconBox: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  googleIconLetter: {
    color: '#4285F4',
    fontSize: 17,
    fontFamily: Typography.font.bold,
    lineHeight: 22,
  },
  googleBtnText: {
    color: '#111',
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.xl,
  },
  // Email fallback — intentionally low-prominence (dev / power-user path)
  emailLink: {
    color: Colors.textMuted,
    fontSize: Typography.size.base,
    fontFamily: Typography.font.regular,
    textDecorationLine: 'underline',
    paddingVertical: Spacing.xs,
  },
  loggingIn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: Spacing.base,
  },
  loggingInText: {
    color: Colors.textSecondary,
    fontSize: Typography.size.md,
    fontFamily: Typography.font.regular,
  },
  hint: {
    color: Colors.textDisabled,
    fontSize: Typography.size.sm,
    fontFamily: Typography.font.regular,
    textAlign: 'center',
    lineHeight: 18,
  },
});
