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
