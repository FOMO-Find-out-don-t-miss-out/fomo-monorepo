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
import { View } from 'react-native';
import { AuthProvider } from '../providers/auth-provider';
import { useAuth } from '../hooks/use-auth';
import { FomoLoadingState } from '../components/ui';
import { Colors } from '../theme';
import { perfMilestone } from '../utils/performance-debug';

// Hold the splash screen until Inter fonts are ready
SplashScreen.preventAutoHideAsync();

// ── Auth gate ─────────────────────────────────────────────────────────────────
// Runs inside <AuthProvider> so it can call useAuth().
// Redirects unauthenticated users to /login and authenticated users away from it.

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, sessionMode } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  // First moment the app can show real (non-loading) content. Since FOMO-179,
  // this no longer waits on /users/me — only on a valid token existing (or
  // being confirmed absent).
  useEffect(() => {
    if (!isLoading) {
      perfMilestone('auth-gate-resolved', { authenticated: isAuthenticated, mode: sessionMode });
    }
  }, [isLoading, isAuthenticated, sessionMode]);

  const onLoginScreen = segments[0] === 'login';
  // On Android, Expo Router receives the fomo://auth/callback deep link at the
  // same time as expo-auth-session's WebBrowser broadcast. Treating the callback
  // route like the login screen prevents AuthGate from firing router.replace('/login')
  // mid-exchange and forcing the user to log in a second time.
  // auth/ has only one route (callback), so checking the first segment is enough.
  const onCallbackRoute = segments[0] === 'auth';
  const onAuthSystemRoute = onLoginScreen || onCallbackRoute;

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated && !onAuthSystemRoute) {
      router.replace('/login');
    } else if (isAuthenticated && onAuthSystemRoute) {
      router.replace('/');
    }
  }, [isAuthenticated, isLoading, onAuthSystemRoute, router]);

  // Block children only when an unauthenticated user is on a protected app route.
  // This prevents a tab screen (e.g. MapView) from mounting then immediately
  // unmounting when the useEffect redirect fires — avoiding Mapbox ViewTagResolver
  // errors. Auth-system routes (/login, /auth/callback) are exempt so the Stack
  // stays mounted and navigation completes on the first attempt.
  const blockChildren = !isLoading && !isAuthenticated && !onAuthSystemRoute;

  if (isLoading || blockChildren) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.background }}>
        <FomoLoadingState />
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
    perfMilestone('root-layout-mounted');
  }, []);

  useEffect(() => {
    if (fontsLoaded || fontError) {
      perfMilestone('fonts-ready', { error: !!fontError });
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) return null;

  return (
    <AuthProvider>
      <View style={{ flex: 1, backgroundColor: Colors.background }}>
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
