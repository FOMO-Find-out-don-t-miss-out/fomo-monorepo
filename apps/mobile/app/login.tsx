import { useAuth } from '../hooks/use-auth';
import { LogIn } from 'lucide-react-native';
import React from 'react';
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

        <Pressable style={styles.loginBtn} onPress={login}>
          <LogIn size={18} color="#fff" strokeWidth={1.5} />
          <Text style={styles.loginBtnText}>Log In</Text>
        </Pressable>

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
  loginBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#A855F7',
    paddingHorizontal: 36,
    paddingVertical: 16,
    borderRadius: 14,
    width: '100%',
    justifyContent: 'center',
  },
  loginBtnText: {
    color: '#fff',
    fontFamily: 'Inter_600SemiBold',
    fontSize: 16,
  },
  hint: {
    color: 'rgba(255,255,255,0.25)',
    fontSize: 12,
    fontFamily: 'Inter_400Regular',
    textAlign: 'center',
    lineHeight: 18,
  },
});
