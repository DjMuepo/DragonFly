import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { createSessionAdapter } from './sessionAdapter';

const SESSION_KEY = 'dragonfly.session-token';
const adapter = createSessionAdapter({
  platform: Platform.OS === 'web' ? 'web' : 'native',
  sessionStorage: typeof window !== 'undefined' ? window.sessionStorage : undefined,
  clearLegacyStorage: () => { if (typeof window !== 'undefined') window.localStorage.removeItem('dragonfly.session-token'); },
  secure: {
    read: () => SecureStore.getItemAsync(SESSION_KEY, { keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY }),
    write: (token) => SecureStore.setItemAsync(SESSION_KEY, token, { keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY }),
    clear: () => SecureStore.deleteItemAsync(SESSION_KEY),
  },
});

export const readSessionToken = () => adapter.read();

export const writeSessionToken = (token: string) => adapter.write(token);

export const clearSessionToken = () => adapter.clear();
