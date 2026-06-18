import '../global.css';

import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
} from '@expo-google-fonts/inter';
import { useFonts } from 'expo-font';
import { useRouter, useSegments, Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { AuthProvider } from '../providers/auth-provider';
import { useAuth } from '../hooks/use-auth';

// Hold the splash screen until Inter fonts are ready
SplashScreen.preventAutoHideAsync();

// ── Auth gate ─────────────────────────────────────────────────────────────────
// Runs inside <AuthProvider> so it can call useAuth().
// Redirects unauthenticated users to /login and authenticated users away from it.

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  const onLoginScreen = segments[0] === 'login';

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated && !onLoginScreen) {
      router.replace('/login');
    } else if (isAuthenticated && onLoginScreen) {
      router.replace('/');
    }
  }, [isAuthenticated, isLoading, onLoginScreen, router]);

  // Hold the spinner while loading OR while a redirect is still pending.
  // Without this, children render for one frame before the useEffect redirect
  // fires — enough to mount a MapView that then immediately unmounts, which
  // causes Mapbox ViewTagResolver errors.
  const redirectPending =
    !isLoading &&
    ((!isAuthenticated && !onLoginScreen) || (isAuthenticated && onLoginScreen));

  if (isLoading || redirectPending) {
    return (
      <View style={{ flex: 1, backgroundColor: '#0B0B0F', alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color="#A855F7" size="large" />
      </View>
    );
  }

  return <>{children}</>;
}

// ── Root layout ───────────────────────────────────────────────────────────────

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    Inter_800ExtraBold,
  });

  useEffect(() => {
    if (fontsLoaded || fontError) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) return null;

  return (
    <AuthProvider>
      <View style={{ flex: 1, backgroundColor: '#0B0B0F' }}>
        <StatusBar style="light" />
        <AuthGate>
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="login" />
          </Stack>
        </AuthGate>
      </View>
    </AuthProvider>
  );
}
