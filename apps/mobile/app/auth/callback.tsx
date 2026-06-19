import * as WebBrowser from 'expo-web-browser';
import { ActivityIndicator, View } from 'react-native';

// expo-auth-session's WebBrowser broadcast resolves promptAsync on Android.
// Expo Router also routes fomo://auth/callback here as a deep link side-effect.
// Showing a spinner while the token exchange completes avoids a blank flash.
WebBrowser.maybeCompleteAuthSession();

export default function AuthCallback() {
  return (
    <View style={{ flex: 1, backgroundColor: '#0B0B0F', alignItems: 'center', justifyContent: 'center' }}>
      <ActivityIndicator color="#A855F7" size="large" />
    </View>
  );
}
