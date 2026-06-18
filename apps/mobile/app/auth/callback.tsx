import * as WebBrowser from 'expo-web-browser';

// Intercepts the fomo://auth/callback deep link on web platforms.
// On Android the WebBrowser module handles this before Expo Router; this
// file is a safety net so the router never shows a 404 on that path.
WebBrowser.maybeCompleteAuthSession();

export default function AuthCallback() {
  return null;
}
