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
        <ActivityIndicator color="#A855F7" size="large" />
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
            <ActivityIndicator color="#A855F7" size="small" />
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
    backgroundColor: '#0B0B0F',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 32,
  },
  logoArea: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  logoRing: {
    width: 96,
    height: 96,
    borderRadius: 48,
    borderWidth: 2,
    borderColor: 'rgba(168,85,247,0.6)',
    backgroundColor: 'rgba(168,85,247,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  logoText: {
    color: '#A855F7',
    fontSize: 48,
    fontFamily: 'Inter_800ExtraBold',
    lineHeight: 56,
  },
  appName: {
    color: '#fff',
    fontSize: 36,
    fontFamily: 'Inter_800ExtraBold',
    letterSpacing: 6,
  },
  tagline: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 14,
    fontFamily: 'Inter_400Regular',
    letterSpacing: 0.3,
  },
  footer: {
    width: '100%',
    alignItems: 'center',
    gap: 14,
    paddingBottom: 8,
  },
  error: {
    color: '#F87171',
    fontSize: 13,
    fontFamily: 'Inter_400Regular',
    textAlign: 'center',
  },
  // Google button — white background follows Google brand guidelines
  googleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 14,
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
    fontFamily: 'Inter_700Bold',
    lineHeight: 22,
  },
  googleBtnText: {
    color: '#111',
    fontFamily: 'Inter_600SemiBold',
    fontSize: 16,
  },
  // Email fallback — intentionally low-prominence (dev / power-user path)
  emailLink: {
    color: 'rgba(255,255,255,0.3)',
    fontSize: 13,
    fontFamily: 'Inter_400Regular',
    textDecorationLine: 'underline',
    paddingVertical: 4,
  },
  loggingIn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 16,
  },
  loggingInText: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 14,
    fontFamily: 'Inter_400Regular',
  },
  hint: {
    color: 'rgba(255,255,255,0.25)',
    fontSize: 12,
    fontFamily: 'Inter_400Regular',
    textAlign: 'center',
    lineHeight: 18,
  },
});
