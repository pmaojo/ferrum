import fs from 'fs';
import path from 'path';

import type { FeatureFlags } from '@shared/flags';

class FeatureFlagService {
  private flags: FeatureFlags = {
    laravelHexagonal: false,
    cliStreaming: false,
    laravelBeta: false,
  };

  constructor() {
    this.loadFromFile();
    this.overrideWithEnv();
  }

  private loadFromFile() {
    const possiblePaths = [
      path.join(process.cwd(), 'config', 'flags.json'),
      path.join(process.cwd(), 'server', 'config', 'flags.json'),
      path.join(process.cwd(), 'scg', 'server', 'config', 'flags.json'),
    ];

    for (const p of possiblePaths) {
      try {
        if (fs.existsSync(p)) {
          const data = fs.readFileSync(p, 'utf-8');
          const parsed = JSON.parse(data);
          this.flags = { ...this.flags, ...parsed };
          break;
        }
      } catch {
        // ignore
      }
    }
  }

  private overrideWithEnv() {
    if (process.env.FLAG_LARAVEL_HEXAGONAL !== undefined) {
      this.flags.laravelHexagonal =
        process.env.FLAG_LARAVEL_HEXAGONAL === 'true';
    }
    if (process.env.FLAG_CLI_STREAMING !== undefined) {
      this.flags.cliStreaming = process.env.FLAG_CLI_STREAMING === 'true';
    }
    if (process.env.FLAG_LARAVEL_BETA !== undefined) {
      this.flags.laravelBeta = process.env.FLAG_LARAVEL_BETA === 'true';
    }
  }

  isEnabled(flag: keyof FeatureFlags): boolean {
    return !!this.flags[flag];
  }

  getAllFlags(): FeatureFlags {
    return this.flags;
  }
}

export const featureFlagService = new FeatureFlagService();
export default FeatureFlagService;
