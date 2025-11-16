import { createContext, useContext, ReactNode } from 'react';
import type { FeatureFlags } from '@shared/flags';

interface AppConfig {
  flags: Partial<FeatureFlags>;
}

const ConfigContext = createContext<AppConfig | null>(null);

export function ConfigProvider({
  config,
  children,
}: {
  config: AppConfig;
  children: ReactNode;
}) {
  return (
    <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>
  );
}

export function useConfig(): AppConfig {
  const ctx = useContext(ConfigContext);
  if (!ctx) {
    throw new Error('useConfig must be used within ConfigProvider');
  }
  return ctx;
}

export function useFeatureFlag(flag: keyof FeatureFlags): boolean {
  const { flags } = useConfig();
  return Boolean(flags[flag]);
}
