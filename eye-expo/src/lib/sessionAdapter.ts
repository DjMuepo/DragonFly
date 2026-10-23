export type SessionAdapterDependencies = {
  platform: 'web' | 'native';
  sessionStorage?: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;
  clearLegacyStorage?: () => void;
  secure: {
    read: () => Promise<string | null>;
    write: (token: string) => Promise<void>;
    clear: () => Promise<void>;
  };
};

export function createSessionAdapter(dependencies: SessionAdapterDependencies) {
  const key = 'dragonfly.session-token';
  return {
    async read(): Promise<string | null> {
      if (dependencies.platform === 'web') {
        dependencies.clearLegacyStorage?.();
        return dependencies.sessionStorage?.getItem(key) || null;
      }
      return dependencies.secure.read();
    },
    async write(token: string): Promise<void> {
      if (dependencies.platform === 'web') {
        dependencies.sessionStorage?.setItem(key, token);
        return;
      }
      await dependencies.secure.write(token);
    },
    async clear(): Promise<void> {
      if (dependencies.platform === 'web') {
        dependencies.sessionStorage?.removeItem(key);
        return;
      }
      await dependencies.secure.clear();
    },
  };
}
