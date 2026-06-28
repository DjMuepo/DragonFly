import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: '#ffffff' },
          headerTintColor: '#111',
          contentStyle: { backgroundColor: '#ffffff' },
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="home" options={{ headerShown: false }} />
        <Stack.Screen name="launch-hub" options={{ title: 'Launch Tools' }} />
        <Stack.Screen name="snap/camera" options={{ title: 'Start Scan' }} />
        <Stack.Screen name="snap/cutout" options={{ title: 'Cutout' }} />
        <Stack.Screen name="snap/process" options={{ title: 'AI Processing' }} />
        <Stack.Screen name="snap/reconstruct" options={{ title: 'Generate 3D' }} />
        <Stack.Screen name="snap/result" options={{ title: '3D Result' }} />
        <Stack.Screen name="snap/viewer" options={{ title: '3D Preview' }} />
        <Stack.Screen name="snap/more-angles" options={{ title: 'Improve Model' }} />
      </Stack>
    </>
  );
}
